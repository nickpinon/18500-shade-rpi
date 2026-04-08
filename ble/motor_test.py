#!/usr/bin/env python3
"""
Standalone motor test — no BLE needed.
Run directly on the Pi:
    sudo python3 motor_test.py
"""

import time
import sys

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: RPi.GPIO not found. Run on the Raspberry Pi.")
    sys.exit(1)

# ── Pin assignments (BCM) ─────────────────────────────────────────────────────
VERTICAL_STEP   = 17
VERTICAL_DIR    = 27
VERTICAL_EN     = 22

HORIZONTAL_STEP = 23
HORIZONTAL_DIR  = 24
HORIZONTAL_EN   = 25

PULSE_SECONDS = 0.0002
STEPS         = 800   # steps per test move

# ── Setup ─────────────────────────────────────────────────────────────────────
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
for pin in [VERTICAL_STEP, VERTICAL_DIR, VERTICAL_EN,
            HORIZONTAL_STEP, HORIZONTAL_DIR, HORIZONTAL_EN]:
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

# Disable both drivers at start (EN active LOW → HIGH = disabled)
GPIO.output(VERTICAL_EN,   GPIO.HIGH)
GPIO.output(HORIZONTAL_EN, GPIO.HIGH)

def step(step_pin, dir_pin, en_pin, forward: bool, steps: int):
    GPIO.output(en_pin,  GPIO.LOW)   # enable driver
    GPIO.output(dir_pin, GPIO.HIGH if forward else GPIO.LOW)
    for _ in range(steps):
        GPIO.output(step_pin, GPIO.HIGH)
        time.sleep(PULSE_SECONDS)
        GPIO.output(step_pin, GPIO.LOW)
        time.sleep(PULSE_SECONDS)
    GPIO.output(en_pin, GPIO.HIGH)   # disable driver

# ── Tests ─────────────────────────────────────────────────────────────────────
try:
    print(f"Testing VERTICAL motor (step={VERTICAL_STEP}, dir={VERTICAL_DIR}, en={VERTICAL_EN})")
    print("  → forward...")
    step(VERTICAL_STEP, VERTICAL_DIR, VERTICAL_EN, forward=True,  steps=STEPS)
    time.sleep(0.5)
    print("  → backward...")
    step(VERTICAL_STEP, VERTICAL_DIR, VERTICAL_EN, forward=False, steps=STEPS)
    time.sleep(0.5)

    print(f"\nTesting HORIZONTAL motor (step={HORIZONTAL_STEP}, dir={HORIZONTAL_DIR}, en={HORIZONTAL_EN})")
    print("  → forward...")
    step(HORIZONTAL_STEP, HORIZONTAL_DIR, HORIZONTAL_EN, forward=True,  steps=STEPS)
    time.sleep(0.5)
    print("  → backward...")
    step(HORIZONTAL_STEP, HORIZONTAL_DIR, HORIZONTAL_EN, forward=False, steps=STEPS)
    time.sleep(0.5)

    print("\nDone. If only one motor moved, the other driver's wiring needs fixing.")

except KeyboardInterrupt:
    print("\nStopped.")

finally:
    GPIO.output(VERTICAL_EN,   GPIO.HIGH)
    GPIO.output(HORIZONTAL_EN, GPIO.HIGH)
    GPIO.cleanup()
