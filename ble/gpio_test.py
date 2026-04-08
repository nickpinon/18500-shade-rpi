#!/usr/bin/env python3
"""
Raw GPIO test — bypasses all BLE and library code.
Tests horizontal motor (pins 23/24/25) directly.
Run: sudo python3 ble/gpio_test.py
"""
import time
import sys

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: RPi.GPIO not found.")
    sys.exit(1)

STEP = 23
DIR  = 24
EN   = 25

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(STEP, GPIO.OUT)
GPIO.setup(DIR,  GPIO.OUT)
GPIO.setup(EN,   GPIO.OUT)

print(f"Pins: STEP={STEP}, DIR={DIR}, EN={EN}")
print("Enabling driver (EN=LOW)...")
GPIO.output(EN, GPIO.LOW)
GPIO.output(DIR, GPIO.HIGH)

print("Pulsing STEP 3200 times — horizontal motor should move...")
for i in range(3200):
    GPIO.output(STEP, GPIO.HIGH)
    time.sleep(0.001)
    GPIO.output(STEP, GPIO.LOW)
    time.sleep(0.001)

GPIO.output(EN, GPIO.HIGH)
GPIO.cleanup()
print("Done. Did the horizontal motor move?")
