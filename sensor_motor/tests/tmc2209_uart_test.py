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
MICROSTEPS = 2 # Set to 2 (Half-stepping) for optimal Python speed as discussed!

# --- Test Parameters ---
TEST_RPMS = [1.0, 5.0, 10.0, 15.0]
TEST_DURATION = 3.0  # Seconds to hold at the target speed
RAMP_DURATION = 1.5  # Seconds to smoothly transition between speeds

def get_step_delay(target_rpm):
    """Calculates the time.sleep() delay for a given output RPM."""
    if target_rpm <= 0.01:
        return 0.1 # Safe fallback
    total_steps_per_rev = MOTOR_STEPS_PER_REV * MICROSTEPS * GEAR_RATIO
    frequency_hz = (target_rpm * total_steps_per_rev) / 60.0
    return 1.0 / (2.0 * frequency_hz)

def transition_speed(chip, start_rpm, target_rpm, duration):
    """Smoothly ramps the speed up or down over a set duration."""
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

    # 1. Initialize TMC2209 via UART
    try:
        tmc = TMC_2209(STEP_PIN, DIR_PIN, EN_PIN, serialport="/dev/ttyAMA0")
        
        if tmc.get_interface_transmission_counter() is None:
            print("[UART] ERROR: Communication failed. Check 1k resistor and RX/TX wiring!")
            return
            
        print("[UART] Communication established.")

        # Configure Driver Digitally
        tmc.set_run_current(60)
        tmc.set_hold_current(30)
        tmc.set_microstepping_res(MICROSTEPS)
        tmc.set_stealthchop(True)
        print(f"[UART] Driver configured: {MICROSTEPS} microsteps, StealthChop ON.")

    except Exception as e:
        print(f"[UART] Error during setup: {e}")
        return

    # 2. Open lgpio chip for high-speed stepping
    try:
        chip = lgpio.gpiochip_open(0)
        print("[MOTOR] Enabling driver...")
        
        # Use the TMC library to enable the motor
        tmc.set_motor_enabled(True)
        time.sleep(0.1)

        # Set initial direction
        lgpio.gpio_write(chip, DIR_PIN, 1)
        
        print("[MOTOR] Starting RPM sweep test with acceleration ramping...")
        current_rpm = TEST_RPMS[0]
        
        while True:
            for next_rpm in TEST_RPMS:
                
                # 1. Ramp to the next speed
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
        print("\n[TEST] Interrupted by user.")
    except Exception as e:
        print(f"[ERROR] Movement failed: {e}")
    finally:
        print("[MOTOR] Cleaning up and disabling driver...")
        tmc.set_motor_enabled(False) # Cuts power to coils so it doesn't get hot
        lgpio.gpiochip_close(chip)

if __name__ == "__main__":
    run_test()