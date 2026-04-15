#!/usr/bin/env python3
"""
Umbrella BLE peripheral — bless GATT server.

Uses the 'bless' library which correctly handles GATT registration on modern
BlueZ / Raspberry Pi OS without the silent rejection issues of raw D-Bus.

Setup (one time):
    pip install bless

Run with:
    sudo python3 ble_server.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
import threading
import time
from dataclasses import asdict, dataclass

try:
    from bless import (
        BlessServer,
        BlessGATTCharacteristic,
        GATTCharacteristicProperties,
        GATTAttributePermissions,
    )
except ImportError:
    print("ERROR: 'bless' not installed.", file=sys.stderr)
    print("Run:  pip install bless", file=sys.stderr)
    sys.exit(1)

try:
    import lgpio
    _GPIO_CHIP = None
    for _chip_num in [4, 0]:
        try:
            _GPIO_CHIP = lgpio.gpiochip_open(_chip_num)
            print(f"GPIO: opened gpiochip{_chip_num}", flush=True)
            break
        except Exception:
            pass
    if _GPIO_CHIP is None:
        raise RuntimeError("No GPIO chip found")
except Exception:
    lgpio = None
    _GPIO_CHIP = None

logging.basicConfig(level=logging.WARNING)

# ── BLE identity ──────────────────────────────────────────────────────────────
DEVICE_NAME       = "UmbrellaPi"
SERVICE_UUID      = "a4f1c6a0-7d5f-4e3d-8a91-102e88d13001"
COMMAND_CHAR_UUID = "a4f1c6a0-7d5f-4e3d-8a91-102e88d13002"
STATUS_CHAR_UUID  = "a4f1c6a0-7d5f-4e3d-8a91-102e88d13003"

# ── GPIO / stepper constants (BCM numbering) ──────────────────────────────────
VERTICAL_STEP_PIN     = 12
VERTICAL_DIR_PIN      = 13
VERTICAL_ENABLE_PIN   = 16
HORIZONTAL_STEP_PIN   = 17
HORIZONTAL_DIR_PIN    = 27
HORIZONTAL_ENABLE_PIN = 22

STEPPER_ENABLE_ACTIVE   = 0
STEPPER_ENABLE_INACTIVE = 1
STEP_FREQUENCY_HZ       = 3000    # slower = more torque, no stalling
MOVE_STEP_COUNT         = 96000   # 60 full rotations at 8-microstep


# ─────────────────────────────────────────────────────────────────────────────
<<<<<<< HEAD:ble/ble_server.py
# Stepper controller
# ─────────────────────────────────────────────────────────────────────────────

class UmbrellaStepperController:
    AXES = {
        "vertical":   {"step": VERTICAL_STEP_PIN,   "dir": VERTICAL_DIR_PIN,   "enable": VERTICAL_ENABLE_PIN},
        "horizontal": {"step": HORIZONTAL_STEP_PIN, "dir": HORIZONTAL_DIR_PIN, "enable": HORIZONTAL_ENABLE_PIN},
    }

    def __init__(self) -> None:
        self.available = lgpio is not None and _GPIO_CHIP is not None
        if not self.available:
            print("GPIO not available — motor commands will only log.", flush=True)
            return
        for axis, pins in self.AXES.items():
            lgpio.gpio_claim_output(_GPIO_CHIP, pins["step"],   0)
            lgpio.gpio_claim_output(_GPIO_CHIP, pins["dir"],    0)
            lgpio.gpio_claim_output(_GPIO_CHIP, pins["enable"], STEPPER_ENABLE_INACTIVE)
            print(f"GPIO setup {axis}: step={pins['step']} dir={pins['dir']} enable={pins['enable']}", flush=True)
        print(f"GPIO ready (lgpio). ENABLE_ACTIVE={STEPPER_ENABLE_ACTIVE}", flush=True)

    def enable_axis(self, axis: str, enabled: bool) -> None:
        if not self.available:
            return
        lgpio.gpio_write(_GPIO_CHIP, self.AXES[axis]["enable"],
                         STEPPER_ENABLE_ACTIVE if enabled else STEPPER_ENABLE_INACTIVE)

    def step_axis(self, axis: str, forward: bool, steps: int = MOVE_STEP_COUNT) -> None:
        pins = self.AXES.get(axis)
        if not pins or not self.available:
            return
        print(f"[GPIO] stepping {axis} {'forward' if forward else 'backward'} {steps} steps "
              f"(step={pins['step']}, dir={pins['dir']}, enable={pins['enable']})", flush=True)
        self.enable_axis(axis, True)
        lgpio.gpio_write(_GPIO_CHIP, pins["dir"], 1 if forward else 0)
        time.sleep(0.001)  # let DIR settle before stepping
        lgpio.tx_pwm(_GPIO_CHIP, pins["step"], STEP_FREQUENCY_HZ, 50, 0, steps)
        while lgpio.tx_busy(_GPIO_CHIP, pins["step"], lgpio.TX_PWM):
            time.sleep(0.005)
        self.enable_axis(axis, False)
        print(f"[GPIO] done stepping {axis}", flush=True)

    def stop_all(self) -> None:
        if not self.available:
            return
        for axis in self.AXES:
            self.enable_axis(axis, False)

    def cleanup(self) -> None:
        if not self.available:
            return
        self.stop_all()
        if _GPIO_CHIP is not None:
            lgpio.gpiochip_close(_GPIO_CHIP)


# ─────────────────────────────────────────────────────────────────────────────
=======
>>>>>>> motor-integrator:sensor_motor/ble/ble_server.py
# Umbrella state
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class UmbrellaState:
    position: int = 52
    mode: str = "Auto"
    moving: bool = False
    connected: bool = True
    target_latitude: float | None = None
    target_longitude: float | None = None
    target_accuracy: float | None = None
    target_timestamp: str | None = None
    manual_direction: str | None = None

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self)).encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Globals (shared between async loop and callbacks)
# ─────────────────────────────────────────────────────────────────────────────

state = UmbrellaState()
state_lock = threading.Lock()
server: BlessServer | None = None


# ─────────────────────────────────────────────────────────────────────────────
# GATT callbacks
# ─────────────────────────────────────────────────────────────────────────────

def read_request(characteristic: BlessGATTCharacteristic, **kwargs) -> bytearray:
    if characteristic.uuid.lower() == STATUS_CHAR_UUID:
        with state_lock:
            return bytearray(state.to_bytes())
    return bytearray()


def write_request(characteristic: BlessGATTCharacteristic, value: Any, **kwargs) -> None:
    print(f"[WRITE] char={characteristic.uuid}  val={bytes(value).hex()}", flush=True)
    if characteristic.uuid.lower() != COMMAND_CHAR_UUID:
        print(f"[WRITE] ignoring — expected {COMMAND_CHAR_UUID}", flush=True)
        return
    try:
        payload = bytes(value).decode("utf-8")
        command = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"Invalid BLE command payload: {exc}", flush=True)
        return

    handle_command(command)


def handle_command(command: dict) -> None:
    global state
    motion = None  # no direct GPIO control anymore

    with state_lock:
        cmd_type = command.get("type")
        if cmd_type == "move":
            direction = (command.get("direction") or "").lower()
            delta = 5 if direction in {"up", "right"} else (-5 if direction in {"down", "left"} else 0)
            state.position = max(0, min(100, state.position + delta))
            state.moving = True
            state.manual_direction = direction
            print(f"Move command received: {direction}", flush=True)

        elif cmd_type == "stop":
            state.moving = False
            state.manual_direction = None
            print("Stop command received", flush=True)

        elif cmd_type == "mode":
            value = command.get("value")

            if isinstance(value, str):
                value = value.strip().lower()

                if value in {"manual", "auto"}:
                    state.mode = value.capitalize()
                    print(f"[BLE] Mode set to {state.mode}", flush=True)
                else:
                    print(f"[BLE] Invalid mode: {value}", flush=True)

        elif cmd_type == "location":
            state.target_latitude  = command.get("latitude")
            state.target_longitude = command.get("longitude")
            state.target_accuracy  = command.get("accuracy")
            state.target_timestamp = command.get("timestamp")
            print(
                f"Location received: {state.target_latitude}, "
                f"{state.target_longitude} (±{state.target_accuracy}m)",
                flush=True,
            )

        else:
            print(f"Unknown command: {command}", flush=True)
            return

    with state_lock:
        if cmd_type == "move":
            state.moving = False

    _push_status()


def _push_status() -> None:
    global server
    if server is None:
        return
    with state_lock:
        data = bytearray(state.to_bytes())
    try:
        char = server.get_characteristic(STATUS_CHAR_UUID)
        if char is not None:
            server.update_value(SERVICE_UUID, STATUS_CHAR_UUID)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Async server
# ─────────────────────────────────────────────────────────────────────────────

# Allow type annotation without importing at top level
from typing import Any  # noqa: E402


async def run() -> None:
    global server

    loop = asyncio.get_event_loop()
    server = BlessServer(name=DEVICE_NAME, loop=loop)
    server.read_request_func = read_request
    server.write_request_func = write_request

    await server.add_new_service(SERVICE_UUID)

    cmd_props = (
        GATTCharacteristicProperties.write
        | GATTCharacteristicProperties.write_without_response
    )
    await server.add_new_characteristic(
        SERVICE_UUID,
        COMMAND_CHAR_UUID,
        cmd_props,
        None,
        GATTAttributePermissions.writeable,
    )

    sta_props = GATTCharacteristicProperties.read | GATTCharacteristicProperties.notify
    with state_lock:
        initial_value = bytearray(state.to_bytes())
    await server.add_new_characteristic(
        SERVICE_UUID,
        STATUS_CHAR_UUID,
        sta_props,
        initial_value,
        GATTAttributePermissions.readable,
    )

    await server.start()

    print(f"\nAdvertising as '{DEVICE_NAME}'", flush=True)
    print(f"Service UUID:  {SERVICE_UUID}", flush=True)
    print(f"Command char:  {COMMAND_CHAR_UUID}", flush=True)
    print(f"Status char:   {STATUS_CHAR_UUID}", flush=True)
    print(
        f"GPIO (BCM): vertical(step={VERTICAL_STEP_PIN}, dir={VERTICAL_DIR_PIN}, "
        f"enable={VERTICAL_ENABLE_PIN}), "
        f"horizontal(step={HORIZONTAL_STEP_PIN}, dir={HORIZONTAL_DIR_PIN}, "
        f"enable={HORIZONTAL_ENABLE_PIN})\n",
        flush=True,
    )
    print("Server running — waiting for connections...", flush=True)

    stop_event = asyncio.Event()

    def _shutdown(signum, frame):
        print("\nShutting down...", flush=True)
        loop.call_soon_threadsafe(stop_event.set)

    # signal.signal(signal.SIGINT,  _shutdown)
    # signal.signal(signal.SIGTERM, _shutdown)

    await stop_event.wait()
    await server.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(run())
