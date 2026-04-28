import time
import lgpio
import sys

# --- Pin Configuration (BCM Numbering) ---
# Reverted to original Horizontal pins
STEP_PIN = 17
DIR_PIN  = 27
EN_PIN   = 22 

# Slower speed for high-torque/low-stall testing
STEP_DELAY = 0.005 

def run_test():
    print("--- TMC2209 Hardware Logic Debug (Continuous) ---")
    
    # 1. Initialize the GPIO chip
    try:
        chip = lgpio.gpiochip_open(0)
    except Exception as e:
        print(f"CRITICAL ERROR: Could not open gpiochip 0. {e}")
        return

    try:
        # 2. Claim pins and force a known state
        # We claim EN as 1 (High/Disabled) initially
        lgpio.gpio_claim_output(chip, EN_PIN, 1)
        lgpio.gpio_claim_output(chip, STEP_PIN, 0)
        lgpio.gpio_claim_output(chip, DIR_PIN, 0)
        
        print(f"Pins claimed. Probing Physical Pin 15 (GPIO 22)...")
        print("Scope should show 3.3V (Logic HIGH) right now.")
        time.sleep(3)

        # 3. Force Enable LOW
        print(">>> FORCING ENABLE LOW (0V)... Check scope now!")
        lgpio.gpio_write(chip, EN_PIN, 0)
        
        # Pause here to let you verify the scope before pulses start
        for i in range(5, 0, -1):
            print(f"Starting pulses in {i}...", end="\r")
            time.sleep(1)
        print("\nStarting movement...")

        # 4. Continuous Pulse Loop
        lgpio.gpio_write(chip, DIR_PIN, 1) # Set direction
        
        step_count = 0
        while True:
            lgpio.gpio_write(chip, STEP_PIN, 1)
            time.sleep(STEP_DELAY)
            lgpio.gpio_write(chip, STEP_PIN, 0)
            time.sleep(STEP_DELAY)
            
            step_count += 1
            if step_count % 100 == 0:
                print(f"Steps taken: {step_count}", end="\r")

    except KeyboardInterrupt:
        print("\nStopping motor...")
    except Exception as e:
        print(f"\nRuntime Error: {e}")
    finally:
        # 5. Cleanup - Return to safe state
        print("Cleaning up and disabling motor...")
        lgpio.gpio_write(chip, EN_PIN, 1)
        lgpio.gpiochip_close(chip)

if __name__ == "__main__":
    run_test()