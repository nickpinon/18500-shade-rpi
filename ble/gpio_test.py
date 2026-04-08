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

h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, STEP, 0)
lgpio.gpio_claim_output(h, DIR,  0)
lgpio.gpio_claim_output(h, EN,   1)  # start disabled

print(f"Pins: STEP={STEP}, DIR={DIR}, EN={EN}")
print("Enabling driver (EN=LOW)...")
lgpio.gpio_write(h, EN,  0)
lgpio.gpio_write(h, DIR, 1)

print("Pulsing STEP 3200 times — horizontal motor should move...")
for i in range(3200):
    lgpio.gpio_write(h, STEP, 1)
    time.sleep(0.001)
    lgpio.gpio_write(h, STEP, 0)
    time.sleep(0.001)

lgpio.gpio_write(h, EN, 1)
lgpio.gpiochip_close(h)
print("Done. Did the horizontal motor move?")
