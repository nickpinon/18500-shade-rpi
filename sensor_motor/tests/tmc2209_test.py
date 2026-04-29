import time
import lgpio

STEP_PIN = 17
DIR_PIN = 27
EN_PIN = 22

# --- Motor & Gearbox Configuration ---
MOTOR_STEPS_PER_REV = 200
GEAR_RATIO = 51
MICROSTEPS = 2

# --- Test Parameters ---
TEST_RPMS = [1.0, 5.0, 10.0, 15.0, 25.0]
TEST_DURATION = 3.0  # Seconds to hold at the target speed
RAMP_DURATION = 1.5  # Seconds to smoothly transition between speeds

def get_step_delay(target_rpm):
    """Calculates the time.sleep() delay for a given output RPM."""
    if target_rpm <= 0.01:
        return 0.1 # Safe fallback to avoid dividing by zero
    total_steps_per_rev = MOTOR_STEPS_PER_REV * MICROSTEPS * GEAR_RATIO
    frequency_hz = (target_rpm * total_steps_per_rev) / 60.0
    return 1.0 / (2.0 * frequency_hz)

def transition_speed(chip, start_rpm, target_rpm, duration):
    """Smoothly ramps the speed up or down over a set duration."""
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        if elapsed >= duration:
            break # Ramp complete
        
        # Linear interpolation: calculate where the RPM should be right now
        progress = elapsed / duration
        current_rpm = start_rpm + (target_rpm - start_rpm) * progress
        
        # Calculate the delay for this exact microsecond and step once
        step_delay = get_step_delay(current_rpm)
        lgpio.gpio_write(chip, STEP_PIN, 1)
        time.sleep(step_delay)
        lgpio.gpio_write(chip, STEP_PIN, 0)
        time.sleep(step_delay)

def run_test():
    chip = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_output(chip, STEP_PIN, 0)
    lgpio.gpio_claim_output(chip, DIR_PIN, 0)
    lgpio.gpio_claim_output(chip, EN_PIN, 1)

    try:
        lgpio.gpio_write(chip, EN_PIN, 0) # Enable the driver
        time.sleep(0.5)
        print("Starting RPM sweep test with acceleration ramping...")
        
        current_rpm = TEST_RPMS[0]
        
        while True:
            for next_rpm in TEST_RPMS:
                
                # 1. Ramp to the next speed (if it's different)
                if current_rpm != next_rpm:
                    print(f"Ramping from {current_rpm:.1f} to {next_rpm:.1f} RPM...")
                    transition_speed(chip, current_rpm, next_rpm, RAMP_DURATION)
                    current_rpm = next_rpm
                
                # 2. Hold at that target speed
                print(f"Holding at: {current_rpm:.1f} RPM for {TEST_DURATION} seconds...")
                step_delay = get_step_delay(current_rpm)
                end_time = time.time() + TEST_DURATION
                
                while time.time() < end_time:
                    lgpio.gpio_write(chip, STEP_PIN, 1)
                    time.sleep(step_delay)
                    lgpio.gpio_write(chip, STEP_PIN, 0)
                    time.sleep(step_delay)
                    
            print("Loop complete. Ramping back to the start...")
            
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
    finally:
        print("Cleaning up GPIO...")
        lgpio.gpio_write(chip, EN_PIN, 1)
        lgpio.gpiochip_close(chip)

if __name__ == "__main__":
    run_test()