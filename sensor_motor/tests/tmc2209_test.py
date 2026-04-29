import time
import lgpio

# --- Vertical Motor Pins (from motor.py) ---
VERT_STEP_PIN = 12
VERT_DIR_PIN  = 13
VERT_EN_PIN   = 16

# --- Horizontal Motor Pins (from motor.py) ---
HORIZ_STEP_PIN = 17
HORIZ_DIR_PIN  = 27
HORIZ_EN_PIN   = 22

# --- Motor & Gearbox Configuration ---
MOTOR_STEPS_PER_REV = 200
GEAR_RATIO = 51
MICROSTEPS = 2 # Assuming you still have the MS1/MS2 pins grounded for Half-stepping

# --- Test Parameters ---
TEST_RPMS = [1.0, 5.0, 10.0, 15.0]
TEST_DURATION = 3.0  # Seconds to hold at the target speed
RAMP_DURATION = 1.5  # Seconds to smoothly transition between speeds

def get_step_delay(target_rpm):
    """Calculates the time.sleep() delay for a given output RPM."""
    if target_rpm <= 0.01:
        return 0.1 
    total_steps_per_rev = MOTOR_STEPS_PER_REV * MICROSTEPS * GEAR_RATIO
    frequency_hz = (target_rpm * total_steps_per_rev) / 60.0
    return 1.0 / (2.0 * frequency_hz)

def transition_speed(chip, start_rpm, target_rpm, duration):
    """Smoothly ramps the speed up or down for BOTH motors."""
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        if elapsed >= duration:
            break
        
        progress = elapsed / duration
        current_rpm = start_rpm + (target_rpm - start_rpm) * progress
        
        step_delay = get_step_delay(current_rpm)
        
        # Step both motors HIGH
        lgpio.gpio_write(chip, VERT_STEP_PIN, 1)
        lgpio.gpio_write(chip, HORIZ_STEP_PIN, 1)
        time.sleep(step_delay)
        
        # Step both motors LOW
        lgpio.gpio_write(chip, VERT_STEP_PIN, 0)
        lgpio.gpio_write(chip, HORIZ_STEP_PIN, 0)
        time.sleep(step_delay)

def run_test():
    chip = lgpio.gpiochip_open(0)
    
    # Claim Vertical Pins
    lgpio.gpio_claim_output(chip, VERT_STEP_PIN, 0)
    lgpio.gpio_claim_output(chip, VERT_DIR_PIN, 0)
    lgpio.gpio_claim_output(chip, VERT_EN_PIN, 1)
    
    # Claim Horizontal Pins
    lgpio.gpio_claim_output(chip, HORIZ_STEP_PIN, 0)
    lgpio.gpio_claim_output(chip, HORIZ_DIR_PIN, 0)
    lgpio.gpio_claim_output(chip, HORIZ_EN_PIN, 1)

    try:
        # Set direction for both motors (1 = Forward)
        lgpio.gpio_write(chip, VERT_DIR_PIN, 0)
        # Enable both drivers (0 = Enabled)
        lgpio.gpio_write(chip, VERT_EN_PIN, 0)
        lgpio.gpio_write(chip, HORIZ_EN_PIN, 0)
        time.sleep(0.5)
        
        print("Starting DUAL MOTOR RPM sweep test with acceleration ramping...")
        current_rpm = TEST_RPMS[0]
        
        while True:
            for next_rpm in TEST_RPMS:
                
                # Ramp to the next speed
                if current_rpm != next_rpm:
                    print(f"Ramping from {current_rpm:.1f} to {next_rpm:.1f} RPM...")
                    transition_speed(chip, current_rpm, next_rpm, RAMP_DURATION)
                    current_rpm = next_rpm
                
                # Hold at target speed
                print(f"Holding at: {current_rpm:.1f} RPM for {TEST_DURATION} seconds...")
                step_delay = get_step_delay(current_rpm)
                end_time = time.time() + TEST_DURATION
                
                while time.time() < end_time:
                    # Step both motors HIGH
                    lgpio.gpio_write(chip, VERT_STEP_PIN, 1)
                    lgpio.gpio_write(chip, HORIZ_STEP_PIN, 1)
                    time.sleep(step_delay)
                    
                    # Step both motors LOW
                    lgpio.gpio_write(chip, VERT_STEP_PIN, 0)
                    lgpio.gpio_write(chip, HORIZ_STEP_PIN, 0)
                    time.sleep(step_delay)
                    
            print("Loop complete. Ramping back to the start...")
            
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
    finally:
        print("Cleaning up GPIO and disabling both motors...")
        # Disable both drivers (1 = Disabled) so they don't overheat
        lgpio.gpio_write(chip, VERT_EN_PIN, 1)
        lgpio.gpio_write(chip, HORIZ_EN_PIN, 1)
        lgpio.gpiochip_close(chip)

if __name__ == "__main__":
    run_test()