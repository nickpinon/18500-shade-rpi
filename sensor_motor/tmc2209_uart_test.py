import time
import lgpio
from TMC_2209.TMC_2209_StepperDriver import TMC_2209

# --- Hardware Configuration (BCM numbering from PINOUT.md) ---
STEP_PIN = 17
DIR_PIN  = 27
EN_PIN   = 22

# Stepper Constants
STEP_PULSE_SECONDS = 0.0002 
MICROSTEPS = 8

def run_test():
    print("--- Starting TMC2209 UART & lgpio Integration Test ---")

    # 1. Initialize TMC2209 FIRST
    # The library claims the pins using gpiozero. Do NOT claim them with lgpio yet.
    try:
        tmc = TMC_2209(STEP_PIN, DIR_PIN, EN_PIN, serialport="/dev/serial0")
        
        if tmc.get_interface_transmission_counter() is None:
            print("[UART] ERROR: Communication failed. Check 1k resistor and RX/TX wiring!")
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
        return

    # 2. Open lgpio chip BUT do not re-claim the pins
    # We use lgpio.gpio_write directly on the pins already held by the system
    try:
        chip = lgpio.gpiochip_open(0)
        print("[MOTOR] Enabling driver and moving...")
        
        # Use the TMC library to enable/disable the motor (handles the logic level for you)
        tmc.set_motor_enabled(True)
        time.sleep(0.1)

        # Set Direction via TMC library or lgpio
        # Note: Since the library 'owns' the pin, it's safer to use tmc.set_direction()
        # but let's try direct lgpio write to see if the RPi 5 allows shared access:
        lgpio.gpio_write(chip, DIR_PIN, 1)
        
        print(f"[MOTOR] Moving 1600 steps...")
        for _ in range(1600):
            lgpio.gpio_write(chip, STEP_PIN, 1)
            time.sleep(STEP_PULSE_SECONDS)
            lgpio.gpio_write(chip, STEP_PIN, 0)
            time.sleep(STEP_PULSE_SECONDS)

        print("[MOTOR] Test move complete.")

    except KeyboardInterrupt:
        print("\n[TEST] Interrupted.")
    except Exception as e:
        print(f"[ERROR] Movement failed: {e}")
    finally:
        tmc.set_motor_enabled(False)
        lgpio.gpiochip_close(chip)
        print("[TEST] Cleanup done.")

if __name__ == "__main__":
    run_test()