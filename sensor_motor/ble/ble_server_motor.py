#!/usr/bin/env python3
"""
Umbrella BLE peripheral with direct motor control (standalone).

Copy of ble_server.py: same GATT layout and JSON commands as the iOS app,
but move/stop immediately drive steppers via sensor_motor.motor — no integrator.

Run from repo root (recommended):

  cd ~/18500-shade-rpi
  source .venv/bin/activate
  sudo python3 sensor_motor/ble/ble_server_motor.py

Tune MANUAL_STEPS_PER_COMMAND if each button tap moves too little / too much.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Repo root on sys.path so `sensor_motor.motor` resolves when run as a script.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sensor_motor.motor import motor

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

logging.basicConfig(level=logging.WARNING)

# ── BLE identity (keep in sync with ble_server.py / iOS app) ─────────────────
DEVICE_NAME       = "UmbrellaPi"
SERVICE_UUID      = "a4f1c6a0-7d5f-4e3d-8a91-102e88d13001"
COMMAND_CHAR_UUID = "a4f1c6a0-7d5f-4e3d-8a91-102e88d13002"
STATUS_CHAR_UUID  = "a4f1c6a0-7d5f-4e3d-8a91-102e88d13003"

# Steps per single "move" BLE command (one tap). Increase for larger jog.
MANUAL_STEPS_PER_COMMAND = 800


# ─────────────────────────────────────────────────────────────────────────────
# Umbrella state (same shape as ble_server.py for app compatibility)
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
    sun_azimuth: float | None = None
    sun_elevation: float | None = None
    sun_source: str | None = None
    manual_direction: str | None = None

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self)).encode("utf-8")


state = UmbrellaState()
state_lock = threading.Lock()
server: BlessServer | None = None


def _apply_move_to_motors(direction: str) -> None:
    """Map app directions to horizontal/vertical step bursts (matches integrator sign sense)."""
    d = (direction or "").lower()
    n = MANUAL_STEPS_PER_COMMAND
    if d == "left":
        motor.step_axis("horizontal", False, steps=n)
    elif d == "right":
        motor.step_axis("horizontal", True, steps=n)
    elif d == "up":
        motor.step_axis("vertical", True, steps=n)
    elif d == "down":
        motor.step_axis("vertical", False, steps=n)
    else:
        print(f"[MOTOR] unknown direction: {direction!r}", flush=True)


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
            state.target_latitude = command.get("latitude")
            state.target_longitude = command.get("longitude")
            state.target_accuracy = command.get("accuracy")
            state.target_timestamp = command.get("timestamp")
            print(
                f"Location received: {state.target_latitude}, "
                f"{state.target_longitude} (±{state.target_accuracy}m)",
                flush=True,
            )

        else:
            print(f"Unknown command: {command}", flush=True)
            return

    # Motor actions outside state_lock (motor uses its own threads / GPIO).
    if cmd_type == "move":
        with state_lock:
            direction = state.manual_direction or ""
        _apply_move_to_motors(direction)
        with state_lock:
            state.moving = False
    elif cmd_type == "stop":
        motor.stop_all()

    _push_status()


def _push_status() -> None:
    global server
    if server is None:
        return
    with state_lock:
        _ = bytearray(state.to_bytes())
    try:
        char = server.get_characteristic(STATUS_CHAR_UUID)
        if char is not None:
            server.update_value(SERVICE_UUID, STATUS_CHAR_UUID)
    except Exception:
        pass


def update_sun_status(azimuth: float, elevation: float, source: str) -> None:
    with state_lock:
        state.sun_azimuth = azimuth
        state.sun_elevation = elevation
        state.sun_source = source
    _push_status()


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

    print(f"\nAdvertising as '{DEVICE_NAME}' (BLE + direct motor)", flush=True)
    print(f"Service UUID:  {SERVICE_UUID}", flush=True)
    print(f"Command char:  {COMMAND_CHAR_UUID}", flush=True)
    print(f"Status char:   {STATUS_CHAR_UUID}", flush=True)
    print(f"Steps per move command: {MANUAL_STEPS_PER_COMMAND}", flush=True)
    print("Server running — waiting for connections...", flush=True)

    stop_event = asyncio.Event()

    def _shutdown(signum, frame):
        print("\nShutting down...", flush=True)
        loop.call_soon_threadsafe(stop_event.set)

    await stop_event.wait()
    await server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    finally:
        motor.cleanup()
