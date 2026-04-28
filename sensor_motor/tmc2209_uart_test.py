import time
import lgpio
import TMC_2209

# --- Hardware Configuration (BCM numbering from PINOUT.md) ---
# Horizontal Motor Pins
STEP_PIN = 17
DIR_PIN  = 27
EN_PIN   = 22

# Stepper Constants
STEP_PULSE_SECONDS = 0.0002  # Matches your current motor.py
MICROSTEPS = 8               # We will set this via UART

def run_test():
    print("--- Starting TMC2209 UART & lgpio Integration Test ---")

    # 1. Initialize lgpio first to claim pins
    try:
        chip = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(chip, STEP_PIN, 0)
        lgpio.gpio_claim_output(chip, DIR_PIN, 0)
        lgpio.gpio_claim_output(chip, EN_PIN, 1) # 1 = Inactive (High) for TMC2209
        print("[LGPIO] Pins claimed successfully.")
    except Exception as e:
        print(f"[LGPIO] Error: {e}")
        return

    # 2. Initialize TMC2209 via UART for configuration
    # Note: We pass the pins so the library knows which driver we are talking to, 
    # but we will handle movement manually with lgpio.
    try:
        # serialport usually maps to /dev/ttyAMA0 on RPi 5
        tmc = TMC_2209(STEP_PIN, DIR_PIN, EN_PIN, serialport="/dev/serial0")
        
        # Verify UART Connection
        if tmc.get_interface_transmission_counter() is None:
            print("[UART] ERROR: Could not communicate with TMC2209. Check wiring/1k resistor.")
            lgpio.gpiochip_close(chip)
            return
            
        print("[UART] Communication established.")

        # Configure Driver Settings
        tmc.set_run_current(60)        # 60% of max current
        tmc.set_hold_current(30)       # 30% to reduce heat when idle
        tmc.set_microstepping_res(MICROSTEPS) 
        tmc.set_stealthchop(True)      # Enable silent mode
        print(f"[UART] Driver configured: {MICROSTEPS} microsteps, StealthChop ON.")

    except Exception as e:
        print(f"[UART] Error during setup: {e}")
        lgpio.gpiochip_close(chip)
        return

    # 3. Movement Test using lgpio logic
    try:
        print("[MOTOR] Enabling driver...")
        lgpio.gpio_write(chip, EN_PIN, 0) # 0 = Active (Low)
        time.sleep(0.1)

        # Set Direction Forward
        lgpio.gpio_write(chip, DIR_PIN, 1)
        
        steps_to_move = 1600 # 1 full rotation at 1/8 microstepping
        print(f"[MOTOR] Moving {steps_to_move} steps forward...")
        
        for _ in range(steps_to_move):
            lgpio.gpio_write(chip, STEP_PIN, 1)
            time.sleep(STEP_PULSE_SECONDS)
            lgpio.gpio_write(chip, STEP_PIN, 0)
            time.sleep(STEP_PULSE_SECONDS)

        time.sleep(0.5)

        # Set Direction Backward
        lgpio.gpio_write(chip, DIR_PIN, 0)
        print(f"[MOTOR] Moving {steps_to_move} steps backward...")
        
        for _ in range(steps_to_move):
            lgpio.gpio_write(chip, STEP_PIN, 1)
            time.sleep(STEP_PULSE_SECONDS)
            lgpio.gpio_write(chip, STEP_PIN, 0)
            time.sleep(STEP_PULSE_SECONDS)

    except KeyboardInterrupt:
        print("\n[TEST] Interrupted by user.")
    finally:
        # 4. Cleanup
        print("[TEST] Cleaning up...")
        lgpio.gpio_write(chip, EN_PIN, 1) # Disable motor
        lgpio.gpiochip_close(chip)
        print("[TEST] Done.")

if __name__ == "__main__":
    run_test()