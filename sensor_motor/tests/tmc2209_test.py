import time
import lgpio

# Original Horizontal Motor Pins
STEP_PIN = 17
DIR_PIN = 27
EN_PIN = 22

# 100Hz Frequency (10ms period)
STEP_DELAY = 0.005 

def run_test():
    print("--- Reverting to Original Continuous Test ---")
    
    try:
        chip = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(chip, STEP_PIN, 0)
        lgpio.gpio_claim_output(chip, DIR_PIN, 0)
        lgpio.gpio_claim_output(chip, EN_PIN, 1) # Start High/Disabled
        print("GPIO initialized. Probing STEP (17) and EN (22)...")
    except Exception as e:
        print(f"GPIO Error: {e}")
        return

    try:
        # Enable the driver
        print("Setting Enable LOW (0V)...")
        lgpio.gpio_write(chip, EN_PIN, 0)
        time.sleep(0.5)

        print("Starting 100Hz pulses. Press Ctrl+C to stop.")
        lgpio.gpio_write(chip, DIR_PIN, 1)
        
        while True:
            lgpio.gpio_write(chip, STEP_PIN, 1)
            time.sleep(STEP_DELAY)
            lgpio.gpio_write(chip, STEP_PIN, 0)
            time.sleep(STEP_DELAY)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        lgpio.gpio_write(chip, EN_PIN, 1) # Disable motor
        lgpio.gpiochip_close(chip)
        print("Cleanup done.")

if __name__ == "__main__":
    run_test()