import time
import lgpio

# Pins from your PINOUT.md
STEP_PIN = 17
DIR_PIN = 27
EN_PIN = 22

# A slower, safer speed to prevent power supply overload
# 0.005 seconds = 10 milliseconds per full step cycle
STEP_DELAY = 0.001 

def run_continuous():
    print("--- Starting Continuous Motor Test ---")
    
    try:
        chip = lgpio.gpiochip_open(0)
        # Claim the logic pins
        lgpio.gpio_claim_output(chip, STEP_PIN, 0)
        lgpio.gpio_claim_output(chip, DIR_PIN, 0)
        lgpio.gpio_claim_output(chip, EN_PIN, 1) # 1 is Disabled
        print("Pins initialized successfully.")
    except Exception as e:
        print(f"Failed to claim pins: {e}")
        return

    try:
        print("Enabling motor...")
        lgpio.gpio_write(chip, EN_PIN, 0) # 0 is Enabled (Active Low)
        time.sleep(0.5)

        # Set direction (1 = forward, 0 = backward)
        lgpio.gpio_write(chip, DIR_PIN, 1)
        
        print("Spinning continuously... Press Ctrl+C to stop.")
        
        # Infinite loop for continuous movement
        while True:
            lgpio.gpio_write(chip, STEP_PIN, 1)
            time.sleep(STEP_DELAY)
            lgpio.gpio_write(chip, STEP_PIN, 0)
            time.sleep(STEP_DELAY)

    except KeyboardInterrupt:
        print("\nStopping motor...")
    finally:
        # Crucial: Disable the motor to cut power draw
        lgpio.gpio_write(chip, EN_PIN, 1)
        lgpio.gpiochip_close(chip)
        print("Cleanup complete.")

if __name__ == "__main__":
    run_continuous()