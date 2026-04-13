"""
Motor Controller Module

Handles all GPIO motor interactions.
"""

import time
import threading

try:
    import lgpio
    _GPIO_CHIP = lgpio.gpiochip_open(0)
except Exception:
    lgpio = None
    _GPIO_CHIP = None


STEP_PULSE_SECONDS = 0.001
MOVE_STEP_COUNT = 50
STEPPER_ENABLE_ACTIVE = 0
STEPPER_ENABLE_INACTIVE = 1


class MotorController:
    AXES = {
        "horizontal": {"step": 17, "dir": 27, "enable": 22},
        "vertical": {"step": 23, "dir": 24, "enable": 25},
    }

    def __init__(self):
        self.available = lgpio is not None and _GPIO_CHIP is not None

        if not self.available:
            print("[MOTOR] GPIO not available, running in simulation mode")
            return

        for axis, pins in self.AXES.items():
            lgpio.gpio_claim_output(_GPIO_CHIP, pins["step"], 0)
            lgpio.gpio_claim_output(_GPIO_CHIP, pins["dir"], 0)
            lgpio.gpio_claim_output(_GPIO_CHIP, pins["enable"], STEPPER_ENABLE_INACTIVE)

        print("[MOTOR] GPIO initialized")

    def enable_axis(self, axis, enabled):
        if not self.available:
            return

        lgpio.gpio_write(
            _GPIO_CHIP,
            self.AXES[axis]["enable"],
            STEPPER_ENABLE_ACTIVE if enabled else STEPPER_ENABLE_INACTIVE,
        )

    def _step_axis_blocking(self, axis, forward, steps):
        if not self.available:
            print(f"[MOTOR-SIM] {axis} {'forward' if forward else 'backward'} {steps}")
            return

        pins = self.AXES[axis]

        self.enable_axis(axis, True)
        lgpio.gpio_write(_GPIO_CHIP, pins["dir"], 1 if forward else 0)

        for _ in range(steps):
            lgpio.gpio_write(_GPIO_CHIP, pins["step"], 1)
            time.sleep(STEP_PULSE_SECONDS)
            lgpio.gpio_write(_GPIO_CHIP, pins["step"], 0)
            time.sleep(STEP_PULSE_SECONDS)

        self.enable_axis(axis, False)

    def step_axis(self, axis, forward, steps=MOVE_STEP_COUNT):
        threading.Thread(
            target=self._step_axis_blocking,
            args=(axis, forward, steps),
            daemon=True,
        ).start()

    def stop_all(self):
        if not self.available:
            print("[MOTOR-SIM] stop_all")
            return

        for axis in self.AXES:
            self.enable_axis(axis, False)

    def cleanup(self):
        if not self.available:
            return

        self.stop_all()
        lgpio.gpiochip_close(_GPIO_CHIP)


motor = MotorController()
