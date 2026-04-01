#!/usr/bin/env python3
"""
Umbrella BLE peripheral — direct BlueZ D-Bus GATT implementation.

Replaces bluezero with direct D-Bus calls so the custom GATT service is
reliably registered with the correct UUIDs on modern BlueZ / Raspberry Pi OS.

Run with:  sudo python3 ble_server.py
"""

from __future__ import annotations

import json
import signal
import threading
import time
from dataclasses import asdict, dataclass

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

try:
    import RPi.GPIO as GPIO
except ModuleNotFoundError:
    GPIO = None  # runs fine without hardware

# ── BLE identity ──────────────────────────────────────────────────────────────
DEVICE_NAME       = "UmbrellaPi"
# BlueZ requires lowercase UUIDs
SERVICE_UUID      = "a4f1c6a0-7d5f-4e3d-8a91-102e88d13001"
COMMAND_CHAR_UUID = "a4f1c6a0-7d5f-4e3d-8a91-102e88d13002"
STATUS_CHAR_UUID  = "a4f1c6a0-7d5f-4e3d-8a91-102e88d13003"

# ── D-Bus / BlueZ interface names ─────────────────────────────────────────────
BLUEZ_SVC        = "org.bluez"
GATT_MGR_IFACE   = "org.bluez.GattManager1"
LE_ADV_MGR_IFACE = "org.bluez.LEAdvertisingManager1"
LE_ADV_IFACE     = "org.bluez.LEAdvertisement1"
GATT_SVC_IFACE   = "org.bluez.GattService1"
GATT_CHR_IFACE   = "org.bluez.GattCharacteristic1"
DBUS_PROP_IFACE  = "org.freedesktop.DBus.Properties"
DBUS_OM_IFACE    = "org.freedesktop.DBus.ObjectManager"

# ── GPIO / stepper constants (BCM numbering) ──────────────────────────────────
VERTICAL_STEP_PIN     = 17
VERTICAL_DIR_PIN      = 27
VERTICAL_ENABLE_PIN   = 22
HORIZONTAL_STEP_PIN   = 23
HORIZONTAL_DIR_PIN    = 24
HORIZONTAL_ENABLE_PIN = 25

STEPPER_ENABLE_ACTIVE   = 0
STEPPER_ENABLE_INACTIVE = 1
STEP_PULSE_SECONDS      = 0.001
MOVE_STEP_COUNT         = 80


# ─────────────────────────────────────────────────────────────────────────────
# Stepper controller
# ─────────────────────────────────────────────────────────────────────────────

class UmbrellaStepperController:
    AXES = {
        "vertical":   {"step": VERTICAL_STEP_PIN,   "dir": VERTICAL_DIR_PIN,   "enable": VERTICAL_ENABLE_PIN},
        "horizontal": {"step": HORIZONTAL_STEP_PIN, "dir": HORIZONTAL_DIR_PIN, "enable": HORIZONTAL_ENABLE_PIN},
    }

    def __init__(self) -> None:
        self.available = GPIO is not None
        if not self.available:
            print("GPIO not available — motor commands will only log.")
            return
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        for pins in self.AXES.values():
            GPIO.setup(pins["step"],   GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(pins["dir"],    GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(pins["enable"], GPIO.OUT, initial=STEPPER_ENABLE_INACTIVE)

    def enable_axis(self, axis: str, enabled: bool) -> None:
        if not self.available:
            return
        GPIO.output(self.AXES[axis]["enable"], STEPPER_ENABLE_ACTIVE if enabled else STEPPER_ENABLE_INACTIVE)

    def step_axis(self, axis: str, forward: bool, steps: int = MOVE_STEP_COUNT) -> None:
        pins = self.AXES.get(axis)
        if not pins or not self.available:
            return
        self.enable_axis(axis, True)
        GPIO.output(pins["dir"], GPIO.HIGH if forward else GPIO.LOW)
        for _ in range(steps):
            GPIO.output(pins["step"], GPIO.HIGH)
            time.sleep(STEP_PULSE_SECONDS)
            GPIO.output(pins["step"], GPIO.LOW)
            time.sleep(STEP_PULSE_SECONDS)
        self.enable_axis(axis, False)

    def stop_all(self) -> None:
        if not self.available:
            return
        for axis in self.AXES:
            self.enable_axis(axis, False)

    def cleanup(self) -> None:
        if not self.available:
            return
        self.stop_all()
        GPIO.cleanup()


# ─────────────────────────────────────────────────────────────────────────────
# Umbrella state
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class UmbrellaState:
    position: int = 52
    mode: str = "Manual"
    moving: bool = False
    connected: bool = True
    target_latitude: float | None = None
    target_longitude: float | None = None
    target_accuracy: float | None = None
    target_timestamp: str | None = None

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self)).encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# D-Bus helpers
# ─────────────────────────────────────────────────────────────────────────────

class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.freedesktop.DBus.Error.InvalidArgs"


class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.NotSupported"


def find_adapter(bus: dbus.SystemBus) -> str:
    """Return the D-Bus path of the first BlueZ adapter that supports GATT."""
    om = dbus.Interface(bus.get_object(BLUEZ_SVC, "/"), DBUS_OM_IFACE)
    for path, ifaces in om.GetManagedObjects().items():
        if GATT_MGR_IFACE in ifaces:
            return path
    raise RuntimeError("No Bluetooth adapter with GattManager found.")


# ─────────────────────────────────────────────────────────────────────────────
# GATT object tree
# ─────────────────────────────────────────────────────────────────────────────

class GattApplication(dbus.service.Object):
    def __init__(self, bus: dbus.SystemBus) -> None:
        self.path = "/"
        self.services: list[GattService] = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self) -> dbus.ObjectPath:
        return dbus.ObjectPath(self.path)

    def add_service(self, service: "GattService") -> None:
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self) -> dict:
        result: dict = {}
        for svc in self.services:
            result[svc.get_path()] = svc.get_properties()
            for chrc in svc.characteristics:
                result[chrc.get_path()] = chrc.get_properties()
        print(f"[D-Bus] GetManagedObjects called — returning {len(result)} objects", flush=True)
        for path, props in result.items():
            for iface, attrs in props.items():
                uuid = attrs.get("UUID", "?")
                print(f"  {path}  iface={iface.split('.')[-1]}  UUID={uuid}", flush=True)
        return result


class GattService(dbus.service.Object):
    BASE = "/org/bluez/umbrella/service"

    def __init__(self, bus: dbus.SystemBus, index: int, uuid: str) -> None:
        self.path = f"{self.BASE}{index}"
        self.uuid = uuid
        self.characteristics: list[GattCharacteristic] = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self) -> dbus.ObjectPath:
        return dbus.ObjectPath(self.path)

    def get_properties(self) -> dict:
        return {
            GATT_SVC_IFACE: {
                "UUID": self.uuid,
                "Primary": dbus.Boolean(True),
                "Characteristics": dbus.Array(
                    [c.get_path() for c in self.characteristics], signature="o"
                ),
            }
        }

    def add_characteristic(self, chrc: "GattCharacteristic") -> None:
        self.characteristics.append(chrc)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface: str) -> dict:
        if interface != GATT_SVC_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_SVC_IFACE]


class GattCharacteristic(dbus.service.Object):
    def __init__(
        self,
        bus: dbus.SystemBus,
        index: int,
        uuid: str,
        flags: list[str],
        service: GattService,
    ) -> None:
        self.path = f"{service.path}/char{index}"
        self.uuid = uuid
        self.flags = flags
        self.service = service
        self.notifying = False
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self) -> dbus.ObjectPath:
        return dbus.ObjectPath(self.path)

    def get_properties(self) -> dict:
        return {
            GATT_CHR_IFACE: {
                "Service": self.service.get_path(),
                "UUID": self.uuid,
                "Flags": dbus.Array(self.flags, signature="s"),
            }
        }

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface: str) -> dict:
        if interface != GATT_CHR_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_CHR_IFACE]

    @dbus.service.signal(DBUS_PROP_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, interface: str, changed: dict, invalidated: list) -> None:
        pass

    @dbus.service.method(GATT_CHR_IFACE, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options: dict) -> list:
        raise NotSupportedException()

    @dbus.service.method(GATT_CHR_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value: list, options: dict) -> None:
        raise NotSupportedException()

    @dbus.service.method(GATT_CHR_IFACE)
    def StartNotify(self) -> None:
        raise NotSupportedException()

    @dbus.service.method(GATT_CHR_IFACE)
    def StopNotify(self) -> None:
        raise NotSupportedException()


class CommandCharacteristic(GattCharacteristic):
    def __init__(self, bus, index, service, on_command) -> None:
        super().__init__(bus, index, COMMAND_CHAR_UUID, ["write", "write-without-response"], service)
        self._on_command = on_command

    @dbus.service.method(GATT_CHR_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value: list, options: dict) -> None:
        try:
            payload = bytes(value).decode("utf-8")
            command = json.loads(payload)
            self._on_command(command)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"Invalid BLE command payload: {exc}")


class StatusCharacteristic(GattCharacteristic):
    def __init__(self, bus, index, service, read_status) -> None:
        super().__init__(bus, index, STATUS_CHAR_UUID, ["read", "notify"], service)
        self._read_status = read_status

    @dbus.service.method(GATT_CHR_IFACE, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options: dict) -> list:
        return dbus.Array(self._read_status(), signature="y")

    @dbus.service.method(GATT_CHR_IFACE)
    def StartNotify(self) -> None:
        self.notifying = True

    @dbus.service.method(GATT_CHR_IFACE)
    def StopNotify(self) -> None:
        self.notifying = False

    def push(self, data: bytes) -> None:
        if self.notifying:
            self.PropertiesChanged(
                GATT_CHR_IFACE,
                {"Value": dbus.Array(list(data), signature="y")},
                [],
            )


# ─────────────────────────────────────────────────────────────────────────────
# BLE advertisement
# ─────────────────────────────────────────────────────────────────────────────

class UmbrellaAdvertisement(dbus.service.Object):
    PATH = "/org/bluez/umbrella/advertisement0"

    def __init__(self, bus: dbus.SystemBus) -> None:
        dbus.service.Object.__init__(self, bus, self.PATH)

    def get_path(self) -> dbus.ObjectPath:
        return dbus.ObjectPath(self.PATH)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface: str) -> dict:
        if interface != LE_ADV_IFACE:
            raise InvalidArgsException()
        return {
            "Type": dbus.String("peripheral"),
            "ServiceUUIDs": dbus.Array([SERVICE_UUID], signature="s"),
            "LocalName": dbus.String(DEVICE_NAME),
            "Includes": dbus.Array(["tx-power"], signature="s"),
        }

    @dbus.service.method(LE_ADV_IFACE)
    def Release(self) -> None:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class UmbrellaBLEPeripheral:
    def __init__(self) -> None:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        self.mainloop = GLib.MainLoop()
        self.state = UmbrellaState()
        self.lock = threading.Lock()
        self.gpio = UmbrellaStepperController()

        adapter_path = find_adapter(self.bus)
        adapter_obj  = self.bus.get_object(BLUEZ_SVC, adapter_path)
        self.gatt_mgr = dbus.Interface(adapter_obj, GATT_MGR_IFACE)
        self.ad_mgr   = dbus.Interface(adapter_obj, LE_ADV_MGR_IFACE)

        # Build GATT tree
        self.app  = GattApplication(self.bus)
        self.svc  = GattService(self.bus, 0, SERVICE_UUID)
        self.cmd  = CommandCharacteristic(self.bus, 0, self.svc, self._handle_command)
        self.sta  = StatusCharacteristic(self.bus, 1, self.svc, self._read_status)
        self.svc.add_characteristic(self.cmd)
        self.svc.add_characteristic(self.sta)
        self.app.add_service(self.svc)

        self.adv = UmbrellaAdvertisement(self.bus)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        self.gatt_mgr.RegisterApplication(
            self.app.get_path(), {},
            reply_handler=self._on_app_registered,
            error_handler=self._on_error,
        )
        self.ad_mgr.RegisterAdvertisement(
            self.adv.get_path(), {},
            reply_handler=lambda: print("Advertisement registered ✓", flush=True),
            error_handler=self._on_error,
        )
        print(f"\nAdvertising as '{DEVICE_NAME}'")
        print(f"Service UUID:  {SERVICE_UUID}")
        print(f"Command char:  {COMMAND_CHAR_UUID}")
        print(f"Status char:   {STATUS_CHAR_UUID}")
        print(
            f"GPIO (BCM): vertical(step={VERTICAL_STEP_PIN}, dir={VERTICAL_DIR_PIN}, "
            f"enable={VERTICAL_ENABLE_PIN}), "
            f"horizontal(step={HORIZONTAL_STEP_PIN}, dir={HORIZONTAL_DIR_PIN}, "
            f"enable={HORIZONTAL_ENABLE_PIN})\n"
        )
        self.mainloop.run()

    def stop(self) -> None:
        print("\nStopping BLE peripheral")
        self.gpio.cleanup()
        for fn in (
            lambda: self.ad_mgr.UnregisterAdvertisement(self.adv.get_path()),
            lambda: self.gatt_mgr.UnregisterApplication(self.app.get_path()),
        ):
            try:
                fn()
            except Exception:
                pass
        self.mainloop.quit()

    def _on_app_registered(self) -> None:
        print("GATT application registered ✓", flush=True)
        try:
            om = dbus.Interface(self.bus.get_object(BLUEZ_SVC, "/"), DBUS_OM_IFACE)
            objects = om.GetManagedObjects()
            print("--- BlueZ GATT table after registration ---", flush=True)
            found = False
            for path, ifaces in objects.items():
                if GATT_SVC_IFACE in ifaces:
                    uuid = ifaces[GATT_SVC_IFACE].get("UUID", "?")
                    print(f"  Service: {uuid}  ({path})", flush=True)
                    found = True
                if GATT_CHR_IFACE in ifaces:
                    uuid = ifaces[GATT_CHR_IFACE].get("UUID", "?")
                    flags = list(ifaces[GATT_CHR_IFACE].get("Flags", []))
                    print(f"    Char:  {uuid}  flags={flags}", flush=True)
                    found = True
            if not found:
                print("  (no GATT services found — registration may have silently failed)", flush=True)
            print("---", flush=True)
        except Exception as exc:
            print(f"  Diagnostic error: {exc}", flush=True)

    def _on_error(self, error) -> None:
        print(f"BLE registration failed: {error}", flush=True)
        self.mainloop.quit()

    # ── status ────────────────────────────────────────────────────────────────

    def _read_status(self) -> list[int]:
        with self.lock:
            return list(self.state.to_bytes())

    def _push_status(self) -> None:
        with self.lock:
            data = self.state.to_bytes()
        self.sta.push(data)

    # ── command handler ───────────────────────────────────────────────────────

    def _handle_command(self, command: dict) -> None:
        cmd_type = command.get("type")
        motion: tuple[str, bool] | None = None

        with self.lock:
            if cmd_type == "move":
                direction = (command.get("direction") or "").lower()
                delta = 5 if direction in {"up", "right"} else (-5 if direction in {"down", "left"} else 0)
                self.state.position = max(0, min(100, self.state.position + delta))
                self.state.moving = True
                motion = {
                    "up":    ("vertical",   True),
                    "down":  ("vertical",   False),
                    "left":  ("horizontal", False),
                    "right": ("horizontal", True),
                }.get(direction)
                print(f"Move command received: {direction}", flush=True)

            elif cmd_type == "stop":
                self.state.moving = False
                print("Stop command received", flush=True)

            elif cmd_type == "mode":
                value = command.get("value")
                if isinstance(value, str) and value:
                    self.state.mode = value
                print(f"Mode command received: {self.state.mode}", flush=True)

            elif cmd_type == "location":
                self.state.target_latitude  = command.get("latitude")
                self.state.target_longitude = command.get("longitude")
                self.state.target_accuracy  = command.get("accuracy")
                self.state.target_timestamp = command.get("timestamp")
                print(
                    f"Location received: {self.state.target_latitude}, "
                    f"{self.state.target_longitude} "
                    f"(±{self.state.target_accuracy}m)"
                )

            else:
                print(f"Unknown command: {command}")
                return

        # Run motor steps in background thread so BLE callbacks stay responsive
        if motion:
            axis, forward = motion
            threading.Thread(target=self.gpio.step_axis, args=(axis, forward), daemon=True).start()
        elif cmd_type == "stop":
            self.gpio.stop_all()

        with self.lock:
            if cmd_type == "move":
                self.state.moving = False

        GLib.idle_add(self._push_status)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    peripheral = UmbrellaBLEPeripheral()

    def shutdown(signum, frame):
        peripheral.stop()

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    peripheral.start()


if __name__ == "__main__":
    main()
