#!/usr/bin/env python3
import time
import sys
import lgpio

# Choose your set based on how you are ACTUALLY wired:
# SET A (from motor.py): STEP=12, DIR=13, EN=16
# SET B (from PINOUT.md): STEP=23, DIR=24, EN=25
V_STEP = 12 
V_DIR  = 23
V_EN   = 16 

# If the test still fails on DIR=13, change V_DIR to a completely 
# different unused pin (like 24 or 26) and move the wire.

PULSE = 0.0005
# Added delay to ensure the driver registers the direction change
DIR_DELAY = 0.1 

def test_vertical():
    h = None
    for chip in [4, 0]: # Try Pi 5 chip then Pi 4 chip
        try:
            h = lgpio.gpiochip_open(chip)
            break
        except: continue
    
    if h is None:
        print("Error: Could not open GPIO")
        return

    # Claim pins
    for p in [V_STEP, V_DIR]: lgpio.gpio_claim_output(h, p, 0)
    lgpio.gpio_claim_output(h, V_EN, 1) # Start disabled

    try:
        while True:
            # --- Forward ---
            print("Moving FORWARD (DIR HIGH)...")
            lgpio.gpio_write(h, V_DIR, 1)
            time.sleep(DIR_DELAY) # Stabilize DIR signal
            lgpio.gpio_write(h, V_EN, 0) # Enable
            for _ in range(800):
                lgpio.gpio_write(h, V_STEP, 1); time.sleep(PULSE)
                lgpio.gpio_write(h, V_STEP, 0); time.sleep(PULSE)
            lgpio.gpio_write(h, V_EN, 1) # Disable
            time.sleep(1)

            # --- Backward ---
            print("Moving BACKWARD (DIR LOW)...")
            lgpio.gpio_write(h, V_DIR, 0)
            time.sleep(DIR_DELAY) # Stabilize DIR signal
            lgpio.gpio_write(h, V_EN, 0) # Enable
            for _ in range(800):
                lgpio.gpio_write(h, V_STEP, 1); time.sleep(PULSE)
                lgpio.gpio_write(h, V_STEP, 0); time.sleep(PULSE)
            lgpio.gpio_write(h, V_EN, 1) # Disable
            time.sleep(1)

    except KeyboardInterrupt:
        pass
    finally:
        lgpio.gpio_write(h, V_EN, 1)
        lgpio.gpiochip_close(h)

test_vertical()