import time
import lgpio

STEP_PIN = 17
DIR_PIN = 27
EN_PIN = 22

# --- Motor & Gearbox Configuration ---
MOTOR_STEPS_PER_REV = 200
GEAR_RATIO = 51
MICROSTEPS = 8 # Assuming 1/8th stepping (default for BTT TMC2209)

# --- Test Parameters ---
TEST_RPMS = [1.0, 5.0, 10.0, 15.0] # The output shaft RPMs you want to test
TEST_DURATION = 3.0 # How many seconds to run each speed

def get_step_delay(target_rpm):
    """Calculates the time.sleep() delay for a given output RPM."""
    if target_rpm <= 0:
        return float('inf')
    total_steps_per_rev = MOTOR_STEPS_PER_REV * MICROSTEPS * GEAR_RATIO
    frequency_hz = (target_rpm * total_steps_per_rev) / 60.0
    return 1.0 / (2.0 * frequency_hz)

def run_test():
    chip = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_output(chip, STEP_PIN, 0)
    lgpio.gpio_claim_output(chip, DIR_PIN, 0)
    lgpio.gpio_claim_output(chip, EN_PIN, 1)

    try:
        lgpio.gpio_write(chip, EN_PIN, 0) # Enable the driver
        time.sleep(0.5)
        print("Starting RPM sweep test...")
        
        while True: # Loop the whole sweep indefinitely
            for rpm in TEST_RPMS:
                print(f"Testing Speed: {rpm} RPM for {TEST_DURATION} seconds...")
                step_delay = get_step_delay(rpm)
                
                # Run at this speed until TEST_DURATION seconds have passed
                end_time = time.time() + TEST_DURATION
                while time.time() < end_time:
                    lgpio.gpio_write(chip, STEP_PIN, 1)
                    time.sleep(step_delay)
                    lgpio.gpio_write(chip, STEP_PIN, 0)
                    time.sleep(step_delay)
                    
            print("Finished sweep. Restarting in 2 seconds...")
            time.sleep(2) # Brief pause before restarting the sweep from the beginning
            
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
    finally:
        print("Cleaning up GPIO...")
        lgpio.gpio_write(chip, EN_PIN, 1) # Disable the driver to prevent overheating
        lgpio.gpiochip_close(chip)

if __name__ == "__main__":
    run_test()