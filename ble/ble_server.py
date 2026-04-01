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
    import RPi.GPIO as GPIO
except ModuleNotFoundError:
    GPIO = None

logging.basicConfig(level=logging.WARNING)

# ── BLE identity ──────────────────────────────────────────────────────────────
DEVICE_NAME       = "UmbrellaPi"
SERVICE_UUID      = "a4f1c6a0-7d5f-4e3d-8a91-102e88d13001"
COMMAND_CHAR_UUID = "a4f1c6a0-7d5f-4e3d-8a91-102e88d13002"
STATUS_CHAR_UUID  = "a4f1c6a0-7d5f-4e3d-8a91-102e88d13003"

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
            print("GPIO not available — motor commands will only log.", flush=True)
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
# Globals (shared between async loop and callbacks)
# ─────────────────────────────────────────────────────────────────────────────

state = UmbrellaState()
state_lock = threading.Lock()
gpio = UmbrellaStepperController()
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
    if characteristic.uuid.lower() != COMMAND_CHAR_UUID:
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
    cmd_type = command.get("type")
    motion: tuple[str, bool] | None = None

    with state_lock:
        if cmd_type == "move":
            direction = (command.get("direction") or "").lower()
            delta = 5 if direction in {"up", "right"} else (-5 if direction in {"down", "left"} else 0)
            state.position = max(0, min(100, state.position + delta))
            state.moving = True
            motion = {
                "up":    ("vertical",   True),
                "down":  ("vertical",   False),
                "left":  ("horizontal", False),
                "right": ("horizontal", True),
            }.get(direction)
            print(f"Move command received: {direction}", flush=True)

        elif cmd_type == "stop":
            state.moving = False
            print("Stop command received", flush=True)

        elif cmd_type == "mode":
            value = command.get("value")
            if isinstance(value, str) and value:
                state.mode = value
            print(f"Mode command received: {state.mode}", flush=True)

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

    if motion:
        axis, forward = motion
        threading.Thread(target=gpio.step_axis, args=(axis, forward), daemon=True).start()
    elif cmd_type == "stop":
        gpio.stop_all()

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
        gpio.cleanup()
        loop.call_soon_threadsafe(stop_event.set)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    await stop_event.wait()
    await server.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(run())
