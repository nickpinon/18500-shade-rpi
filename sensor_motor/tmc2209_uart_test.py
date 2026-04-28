import time
import lgpio
from TMC_2209.TMC_2209_StepperDriver import TMC_2209

# --- Hardware Configuration (BCM numbering from PINOUT.md) ---
# Using Horizontal Motor pins to avoid the IMU interrupt conflict
STEP_PIN = 17
DIR_PIN  = 27
EN_PIN   = 22

# Stepper Constants from your motor.py
STEP_PULSE_SECONDS = 0.0002 
MICROSTEPS = 8

def run_test():
    print("--- Starting TMC2209 UART & lgpio Integration Test ---")

    # 1. Initialize lgpio to claim pins
    try:
        chip = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(chip, STEP_PIN, 0)
        lgpio.gpio_claim_output(chip, DIR_PIN, 0)
        lgpio.gpio_claim_output(chip, EN_PIN, 1) # 1 = Inactive/High
        print("[LGPIO] Pins claimed successfully.")
    except Exception as e:
        print(f"[LGPIO] Error: {e}")
        return

    # 2. Initialize TMC2209 via UART for configuration
    try:
        # Pass pins and serial port
        tmc = TMC_2209(STEP_PIN, DIR_PIN, EN_PIN, serialport="/dev/serial0")
        
        # Verify communication
        if tmc.get_interface_transmission_counter() is None:
            print("[UART] ERROR: Communication failed. Check 1k resistor and RX/TX wiring!")
            lgpio.gpiochip_close(chip)
            return
            
        print("[UART] Communication established.")

        # Configure Driver
        tmc.set_run_current(60)
        tmc.set_hold_current(30)
        tmc.set_microstepping_res(MICROSTEPS)
        tmc.set_stealthchop(True)
        print(f"[UART] Driver configured: {MICROSTEPS} microsteps, StealthChop ON.")

    except Exception as e:
        print(f"[UART] Error during setup: {e}")
        lgpio.gpiochip_close(chip)
        return

    # 3. Movement Test using lgpio
    try:
        print("[MOTOR] Enabling driver and moving...")
        lgpio.gpio_write(chip, EN_PIN, 0) # 0 = Active/Low
        time.sleep(0.1)

        # Set Direction Forward
        lgpio.gpio_write(chip, DIR_PIN, 1)
        
        # 1 full rotation (200 steps * 8 microsteps = 1600)
        for _ in range(1600):
            lgpio.gpio_write(chip, STEP_PIN, 1)
            time.sleep(STEP_PULSE_SECONDS)
            lgpio.gpio_write(chip, STEP_PIN, 0)
            time.sleep(STEP_PULSE_SECONDS)

        print("[MOTOR] Test move complete.")

    except KeyboardInterrupt:
        print("\n[TEST] Interrupted.")
    finally:
        lgpio.gpio_write(chip, EN_PIN, 1) # Disable motor
        lgpio.gpiochip_close(chip)
        print("[TEST] Cleanup done.")

if __name__ == "__main__":
    run_test()