import time
import lgpio
from TMC_2209.TMC_2209_StepperDriver import TMC_2209

# --- Hardware Configuration (BCM numbering from PINOUT.md) ---
STEP_PIN = 17
DIR_PIN  = 27
EN_PIN   = 22

# --- Motor & Gearbox Configuration ---
MOTOR_STEPS_PER_REV = 200
GEAR_RATIO = 51
MICROSTEPS = 2 # Set to 2 (Half-stepping) for optimal Python speed

# --- Test Parameters ---
TEST_RPMS = [1.0, 5.0, 10.0, 15.0]
TEST_DURATION = 3.0  
RAMP_DURATION = 1.5  

def get_step_delay(target_rpm):
    if target_rpm <= 0.01:
        return 0.1 
    total_steps_per_rev = MOTOR_STEPS_PER_REV * MICROSTEPS * GEAR_RATIO
    frequency_hz = (target_rpm * total_steps_per_rev) / 60.0
    return 1.0 / (2.0 * frequency_hz)

def transition_speed(chip, start_rpm, target_rpm, duration):
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        if elapsed >= duration:
            break
        progress = elapsed / duration
        current_rpm = start_rpm + (target_rpm - start_rpm) * progress
        
        step_delay = get_step_delay(current_rpm)
        lgpio.gpio_write(chip, STEP_PIN, 1)
        time.sleep(step_delay)
        lgpio.gpio_write(chip, STEP_PIN, 0)
        time.sleep(step_delay)

def run_test():
    print("--- Starting TMC2209 UART & lgpio Integration Test ---")

    try:
        # 1. Initialize TMC2209 via UART
        tmc = TMC_2209(STEP_PIN, DIR_PIN, EN_PIN, serialport="/dev/ttyAMA0")
        
        # Configure Driver Digitally (Using correct camelCase library methods!)
        tmc.setSpreadCycle(False) # False = StealthChop ON (Silent mode)
        tmc.setCurrent(500)       # Set current in milliamps (500mA is a safe baseline)
        tmc.setMicrosteppingResolution(MICROSTEPS)
        
        print(f"[UART] Driver configured: {MICROSTEPS} microsteps, StealthChop ON.")

    except Exception as e:
        print(f"[UART] Error during setup: {e}")
        return

    try:
        # 2. Open lgpio chip for high-speed stepping
        chip = lgpio.gpiochip_open(0)
        print("[MOTOR] Enabling driver...")
        
        # Corrected library enable method
        tmc.setMotorEnabled(True)
        time.sleep(0.1)

        lgpio.gpio_write(chip, DIR_PIN, 1)
        
        print("[MOTOR] Starting RPM sweep test...")
        current_rpm = TEST_RPMS[0]
        
        while True:
            for next_rpm in TEST_RPMS:
                if current_rpm != next_rpm:
                    transition_speed(chip, current_rpm, next_rpm, RAMP_DURATION)
                    current_rpm = next_rpm
                
                step_delay = get_step_delay(current_rpm)
                end_time = time.time() + TEST_DURATION
                
                while time.time() < end_time:
                    lgpio.gpio_write(chip, STEP_PIN, 1)
                    time.sleep(step_delay)
                    lgpio.gpio_write(chip, STEP_PIN, 0)
                    time.sleep(step_delay)
                    
    except KeyboardInterrupt:
        print("\n[TEST] Interrupted by user.")
    except Exception as e:
        print(f"[ERROR] Movement failed: {e}")
    finally:
        print("[MOTOR] Cleaning up...")
        # Corrected library disable method
        tmc.setMotorEnabled(False) 
        lgpio.gpiochip_close(chip)

if __name__ == "__main__":
    run_test()