#!/usr/bin/env python3
"""
Raw GPIO test for horizontal motor (lgpio — Pi 5 compatible).
Run: sudo python3 ble/gpio_test.py
"""
import time
import sys

try:
    import lgpio
except ImportError:
    print("ERROR: lgpio not found. Run: sudo apt install python3-lgpio")
    sys.exit(1)

STEP = 23
DIR  = 24
EN   = 25

# Pi 5 uses gpiochip4 for the 40-pin header; Pi 4 and earlier use gpiochip0.
# Try both and use whichever opens successfully.
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

lgpio.gpio_claim_output(h, STEP, 0)
lgpio.gpio_claim_output(h, DIR,  0)
lgpio.gpio_claim_output(h, EN,   1)  # start disabled

print(f"Pins: STEP={STEP}, DIR={DIR}, EN={EN}")
print("Enabling driver (EN=LOW)...")
lgpio.gpio_write(h, EN,  0)
lgpio.gpio_write(h, DIR, 1)

print("Pulsing STEP 3200 times — motor should move...")
for i in range(3200):
    lgpio.gpio_write(h, STEP, 1)
    time.sleep(0.001)
    lgpio.gpio_write(h, STEP, 0)
    time.sleep(0.001)

lgpio.gpio_write(h, EN, 1)
lgpio.gpiochip_close(h)
print("Done. Did the motor move?")
