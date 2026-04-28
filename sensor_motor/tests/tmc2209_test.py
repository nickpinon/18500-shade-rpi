import time
import lgpio

# Pins from your PINOUT.md
STEP_PIN = 17
DIR_PIN = 27
EN_PIN = 22

def test_standalone():
    print("--- Testing Standalone Step/Dir Movement ---")
    
    try:
        chip = lgpio.gpiochip_open(0)
        # Claim pins
        lgpio.gpio_claim_output(chip, STEP_PIN, 0)
        lgpio.gpio_claim_output(chip, DIR_PIN, 0)
        lgpio.gpio_claim_output(chip, EN_PIN, 1) # Start Disabled (High)
        print("Pins initialized.")
    except Exception as e:
        print(f"Failed to claim pins: {e}")
        return

    try:
        print("Enabling motor... (Should hear a slight hiss or lock up)")
        lgpio.gpio_write(chip, EN_PIN, 0) # Enable (Low)
        time.sleep(0.5)

        print("Moving forward...")
        lgpio.gpio_write(chip, DIR_PIN, 1)
        for _ in range(800): # Just a short burst
            lgpio.gpio_write(chip, STEP_PIN, 1)
            time.sleep(0.001) # Slower pulse to be safe
            lgpio.gpio_write(chip, STEP_PIN, 0)
            time.sleep(0.001)
            
        time.sleep(0.5)
        
        print("Moving backward...")
        lgpio.gpio_write(chip, DIR_PIN, 0)
        for _ in range(800):
            lgpio.gpio_write(chip, STEP_PIN, 1)
            time.sleep(0.001)
            lgpio.gpio_write(chip, STEP_PIN, 0)
            time.sleep(0.001)
            
        print("Done.")

    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        lgpio.gpio_write(chip, EN_PIN, 1) # Disable
        lgpio.gpiochip_close(chip)

if __name__ == "__main__":
    test_standalone()