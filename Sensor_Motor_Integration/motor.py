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


# ── GPIO / stepper constants (BCM numbering) ──────────────────────────────────
VERTICAL_STEP_PIN     = 12
VERTICAL_DIR_PIN      = 13
VERTICAL_ENABLE_PIN   = 16
HORIZONTAL_STEP_PIN   = 17
HORIZONTAL_DIR_PIN    = 27
HORIZONTAL_ENABLE_PIN = 22

STEPPER_ENABLE_ACTIVE   = 0
STEPPER_ENABLE_INACTIVE = 1
STEP_PULSE_SECONDS      = 0.0002
MOVE_STEP_COUNT         = 12800


class MotorController:
    AXES = {
        "vertical":   {"step": VERTICAL_STEP_PIN,   "dir": VERTICAL_DIR_PIN,   "enable": VERTICAL_ENABLE_PIN},
        "horizontal": {"step": HORIZONTAL_STEP_PIN, "dir": HORIZONTAL_DIR_PIN, "enable": HORIZONTAL_ENABLE_PIN},
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
