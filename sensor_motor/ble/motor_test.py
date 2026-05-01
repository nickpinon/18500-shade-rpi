#!/usr/bin/env python3
"""
Standalone motor test (lgpio — Pi 5 compatible).
Run: sudo python3 sensor_motor/ble/motor_test.py
"""

import time
import sys

try:
    import lgpio
except ImportError:
    print("ERROR: lgpio not found. Run: sudo apt install python3-lgpio")
    sys.exit(1)

# ── Pin assignments (BCM) ─────────────────────────────────────────────────────
VERTICAL_STEP   = 12
VERTICAL_DIR    = 13
VERTICAL_EN     = 16

HORIZONTAL_STEP = 17
HORIZONTAL_DIR  = 27
HORIZONTAL_EN   = 22

# Shorter pulse = faster stepping (raise if motor skips).
PULSE_SECONDS = 0.0002
# More steps = longer travel per forward/backward segment.
STEPS = 5000
# Forward + backward cycles per motor.
MOTOR_REPEAT = 3


def _run_both_directions(label: str, step_pin: int, dir_pin: int, en_pin: int) -> None:
    print(f"\n=== {label} (step={step_pin}, dir={dir_pin}, en={en_pin}) ===", flush=True)
    for rep in range(1, MOTOR_REPEAT + 1):
        print(f"  Cycle {rep}/{MOTOR_REPEAT} — forward...", flush=True)
        step(step_pin, dir_pin, en_pin, forward=True, steps=STEPS)
        time.sleep(0.5)
        print(f"  Cycle {rep}/{MOTOR_REPEAT} — backward...", flush=True)
        step(step_pin, dir_pin, en_pin, forward=False, steps=STEPS)
        time.sleep(0.5)


# ── Setup ─────────────────────────────────────────────────────────────────────
h = None
for chip in [4, 0]:
    try:
        h = lgpio.gpiochip_open(chip)
        print(f"Opened gpiochip{chip}")
        break
    except Exception as e:
        print(f"gpiochip{chip} failed: {e}")
if h is None:
    print("ERROR: could not open any GPIO chip")
    sys.exit(1)

for pin in [VERTICAL_STEP, VERTICAL_DIR, HORIZONTAL_STEP, HORIZONTAL_DIR]:
    lgpio.gpio_claim_output(h, pin, 0)

for pin in [VERTICAL_EN, HORIZONTAL_EN]:
    lgpio.gpio_claim_output(h, pin, 1)  # start disabled (HIGH)


def step(step_pin, dir_pin, en_pin, forward: bool, steps: int):
    lgpio.gpio_write(h, en_pin,  0)   # enable (active LOW)
    lgpio.gpio_write(h, dir_pin, 1 if forward else 0)
    for _ in range(steps):
        lgpio.gpio_write(h, step_pin, 1)
        time.sleep(PULSE_SECONDS)
        lgpio.gpio_write(h, step_pin, 0)
        time.sleep(PULSE_SECONDS)
    lgpio.gpio_write(h, en_pin, 1)    # disable


# ── Tests: each motor runs forward then backward, repeated ─────────────────────
try:
    print(
        f"Motor test | pulse={PULSE_SECONDS}s, steps={STEPS}, "
        f"repeat={MOTOR_REPEAT} per axis",
        flush=True,
    )
    _run_both_directions("VERTICAL", VERTICAL_STEP, VERTICAL_DIR, VERTICAL_EN)
    _run_both_directions("HORIZONTAL", HORIZONTAL_STEP, HORIZONTAL_DIR, HORIZONTAL_EN)
    print("\nDone.", flush=True)

except KeyboardInterrupt:
    print("\nStopped.", flush=True)

finally:
    lgpio.gpio_write(h, VERTICAL_EN, 1)
    lgpio.gpio_write(h, HORIZONTAL_EN, 1)
    lgpio.gpiochip_close(h)
