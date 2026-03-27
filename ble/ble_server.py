#!/usr/bin/env python3
"""
Starter BLE peripheral for the Umbrella App.

This script advertises a custom BLE service for the iPhone app and keeps a
simple in-memory umbrella state. Replace the placeholder movement logic with
your GPIO or motor controller integration when the hardware is ready.
"""

from __future__ import annotations

import json
import signal
import threading
import time
from dataclasses import dataclass, asdict

from bluezero import adapter, peripheral


DEVICE_NAME = "UmbrellaPi"
SERVICE_UUID = "A4F1C6A0-7D5F-4E3D-8A91-102E88D13001"
COMMAND_CHARACTERISTIC_UUID = "A4F1C6A0-7D5F-4E3D-8A91-102E88D13002"
STATUS_CHARACTERISTIC_UUID = "A4F1C6A0-7D5F-4E3D-8A91-102E88D13003"


@dataclass
class UmbrellaState:
    position: int = 52
    mode: str = "Manual"
    moving: bool = False
    connected: bool = True

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self)).encode("utf-8")


class UmbrellaBLEPeripheral:
    def __init__(self) -> None:
        adapters = list(adapter.Adapter.available())
        if not adapters:
            raise RuntimeError("No Bluetooth adapter found on this Raspberry Pi.")

        self.state = UmbrellaState()
        self.lock = threading.Lock()
        self.status_subscribed = False
        self.ble = peripheral.Peripheral(
            adapter_addr=adapters[0].address,
            local_name=DEVICE_NAME,
            appearance=0,
        )

        self.ble.add_service(srv_id=1, uuid=SERVICE_UUID, primary=True)
        self.ble.add_characteristic(
            srv_id=1,
            chr_id=1,
            uuid=COMMAND_CHARACTERISTIC_UUID,
            value=[],
            notifying=False,
            flags=["write", "write-without-response"],
            write_callback=self.on_command_written,
        )
        self.ble.add_characteristic(
            srv_id=1,
            chr_id=2,
            uuid=STATUS_CHARACTERISTIC_UUID,
            value=list(self.state.to_bytes()),
            notifying=True,
            flags=["read", "notify"],
            read_callback=self.read_status,
            notify_callback=self.on_status_notify,
        )

    def start(self) -> None:
        print(f"Advertising BLE umbrella service as {DEVICE_NAME}")
        print(f"Service UUID: {SERVICE_UUID}")
        self.ble.publish()

    def stop(self) -> None:
        print("Stopping BLE peripheral")
        self.ble.unpublish()

    def read_status(self) -> list[int]:
        with self.lock:
            return list(self.state.to_bytes())

    def on_status_notify(self, notifying: bool, characteristic) -> None:
        self.status_subscribed = notifying
        if notifying:
            self.push_status()

    def on_command_written(self, value, options) -> None:
        try:
            payload = bytes(value).decode("utf-8")
            command = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            print(f"Invalid command payload: {error}")
            return

        self.handle_command(command)
        self.push_status()

    def handle_command(self, command: dict) -> None:
        command_type = command.get("type")

        with self.lock:
            if command_type == "move":
                direction = (command.get("direction") or "").lower()
                delta = 0

                if direction in {"up", "right"}:
                    delta = 5
                elif direction in {"down", "left"}:
                    delta = -5

                self.state.position = max(0, min(100, self.state.position + delta))
                self.state.moving = True
                print(f"Move command received: {direction}")

            elif command_type == "stop":
                self.state.moving = False
                print("Stop command received")

            elif command_type == "mode":
                value = command.get("value")
                if isinstance(value, str) and value:
                    self.state.mode = value
                print(f"Mode command received: {self.state.mode}")

            else:
                print(f"Unknown command: {command}")
                return

        # Placeholder for real motor logic.
        time.sleep(0.1)

        with self.lock:
            if command_type == "move":
                self.state.moving = False

    def push_status(self) -> None:
        try:
            self.ble.update_characteristic_value(1, 2, list(self.read_status()))
        except AttributeError:
            # Older bluezero versions can still satisfy reads even if this helper
            # is missing, so keep the server alive for development setups.
            pass


def main() -> None:
    ble_peripheral = UmbrellaBLEPeripheral()

    def shutdown_handler(signum, frame) -> None:
        ble_peripheral.stop()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    ble_peripheral.start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
