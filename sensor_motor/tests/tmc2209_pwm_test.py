import time
import lgpio

# --- CHANGED: Must be a Hardware PWM Pin ---
STEP_PIN = 18 
DIR_PIN = 27
EN_PIN = 22

# --- Motor & Gearbox Configuration ---
MOTOR_STEPS_PER_REV = 200
GEAR_RATIO = 51
MICROSTEPS = 2 # Assuming you kept MS1/MS2 grounded (1/2 or Full step is fine here!)

def get_frequency(target_rpm):
    """Returns the required Hz (steps per second) for a target RPM."""
    if target_rpm <= 0.01:
        return 0
    total_steps_per_rev = MOTOR_STEPS_PER_REV * MICROSTEPS * GEAR_RATIO
    frequency_hz = (target_rpm * total_steps_per_rev) / 60.0
    return int(frequency_hz) # lgpio requires frequency to be an integer

def run_test():
    chip = lgpio.gpiochip_open(0)
    
    # Notice we don't need to claim the STEP_PIN as an output, 
    # lgpio.tx_pwm handles that automatically.
    lgpio.gpio_claim_output(chip, DIR_PIN, 0)
    lgpio.gpio_claim_output(chip, EN_PIN, 1)

    try:
        lgpio.gpio_write(chip, EN_PIN, 0) # Enable the driver
        time.sleep(0.5)
        
        target_rpm = 15.0
        freq = get_frequency(target_rpm)
        
        print(f"Spinning at {target_rpm} RPM ({freq} Hz) using Hardware PWM...")
        
        # Start the hardware pulses
        # lgpio.tx_pwm(chip, pin, frequency_hz, duty_cycle_percentage)
        # We use 50.0 for a perfect 50% ON / 50% OFF square wave
        lgpio.tx_pwm(chip, STEP_PIN, freq, 50.0) 
        
        # Python can now just do nothing. The hardware is doing the work!
        time.sleep(5.0) 
        
        print("Stopping...")
        # Turn off the PWM pulses
        lgpio.tx_pwm(chip, STEP_PIN, freq, 0.0)
            
    except KeyboardInterrupt:
        print("\nTest stopped.")
    finally:
        lgpio.tx_pwm(chip, STEP_PIN, 1000, 0.0) # Ensure PWM is off
        lgpio.gpio_write(chip, EN_PIN, 1)    # Disable driver
        lgpio.gpiochip_close(chip)

if __name__ == "__main__":
    run_test()