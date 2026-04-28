import time
import lgpio
from tmc2209 import TMC2209

# --- GPIO Configuration ---
STEP_PIN = 17
DIR_PIN = 27
EN_PIN = 22

# --- Setup lgpio ---
try:
    chip = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_output(chip, STEP_PIN, 0)
    lgpio.gpio_claim_output(chip, DIR_PIN, 0)
    lgpio.gpio_claim_output(chip, EN_PIN, 1) # 1 is disabled/inactive for stepper
except Exception as e:
    print(f"Failed to initialize lgpio: {e}")
    exit(1)

# --- Setup TMC2209 UART ---
print("Initializing TMC2209 via UART...")
# Use /dev/serial0 which maps to UART0 (GPIO 14/15)
tmc = TMC2209_uart("/dev/serial0", baudrate=115200)

# Configure the driver parameters via UART
tmc.set_mres(8)           # 256 microsteps (smooth movement)
tmc.set_irun_ilhold(16, 8) # Set run current to 16/31, hold current to 8/31
tmc.set_spreadcycle(False) # Use StealthChop (super quiet mode)

# Check if we can communicate with the chip
if tmc.read_gconf() is None:
    print("ERROR: Could not read from TMC2209. Check your UART wiring and 1k resistor!")
    lgpio.gpiochip_close(chip)
    exit(1)

print("TMC2209 Connected successfully!")

def run_motor(steps, direction, delay=0.001):
    # Enable the motor driver (active low)
    lgpio.gpio_write(chip, EN_PIN, 0)
    
    # Set direction
    lgpio.gpio_write(chip, DIR_PIN, direction)
    
    print(f"Moving {steps} steps...")
    for _ in range(steps):
        lgpio.gpio_write(chip, STEP_PIN, 1)
        time.sleep(delay)
        lgpio.gpio_write(chip, STEP_PIN, 0)
        time.sleep(delay)
        
    # Disable motor to prevent overheating during testing
    lgpio.gpio_write(chip, EN_PIN, 1)

try:
    # Move forward
    run_motor(1000, direction=1, delay=0.0005)
    time.sleep(1)
    
    # Move backward
    run_motor(1000, direction=0, delay=0.0005)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    # Cleanup
    lgpio.gpio_write(chip, EN_PIN, 1)
    lgpio.gpiochip_close(chip)
    del tmc
    print("Cleanup complete.")