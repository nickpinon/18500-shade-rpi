import time
import lgpio
from rpi_hardware_pwm import HardwarePWM

# --- Pin Configuration ---
# STEP_PIN is handled completely by HardwarePWM now (GPIO 18 = Channel 2)
DIR_PIN = 27
EN_PIN = 22

# --- Motor Configuration ---
MOTOR_STEPS_PER_REV = 200
GEAR_RATIO = 51
MICROSTEPS = 2 

def get_frequency(target_rpm):
    if target_rpm <= 0.01:
        return 10  # HardwarePWM expects a minimum frequency > 0
    total_steps_per_rev = MOTOR_STEPS_PER_REV * MICROSTEPS * GEAR_RATIO
    frequency_hz = (target_rpm * total_steps_per_rev) / 60.0
    return int(frequency_hz)

def run_test():
    # Setup the standard GPIO pins
    chip = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_output(chip, DIR_PIN, 0)
    lgpio.gpio_claim_output(chip, EN_PIN, 1)

    # Initialize Pi 5 Hardware PWM on GPIO 18 (PWM Channel 2, Chip 0)
    # We set a dummy frequency of 10Hz to start.
    stepper_pwm = HardwarePWM(pwm_channel=2, hz=10, chip=0)

    try:
        lgpio.gpio_write(chip, EN_PIN, 0) # Enable Driver
        time.sleep(0.5)
        
        target_rpm = 15.0
        freq = get_frequency(target_rpm)
        
        print(f"Spinning at {target_rpm} RPM ({freq} Hz) using True Hardware PWM...")
        
        # Apply the target frequency and start the pulse (50% Duty Cycle)
        stepper_pwm.change_frequency(freq)
        stepper_pwm.start(50.0) 
        
        # Python goes to sleep, the hardware handles the stepping!
        time.sleep(5.0) 
        
        print("Stopping...")
        stepper_pwm.stop()
            
    except KeyboardInterrupt:
        print("\nTest stopped.")
    finally:
        stepper_pwm.stop()
        lgpio.gpio_write(chip, EN_PIN, 1) # Disable Driver
        lgpio.gpiochip_close(chip)

if __name__ == "__main__":
    run_test()