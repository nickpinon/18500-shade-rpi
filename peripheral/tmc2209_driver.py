from gpiozero import OutputDevice
import time

# 1. Define the pins
# EN is active-LOW, so setting initial_value=True actually keeps the motor OFF until we are ready.
en_pin = OutputDevice(21, initial_value=True) 
step_pin = OutputDevice(16, initial_value=False)
dir_pin = OutputDevice(20, initial_value=False)

def spin_motor(steps, delay=0.001):
    """Generates manual step pulses."""
    for _ in range(steps):
        step_pin.on()
        time.sleep(delay)
        step_pin.off()
        time.sleep(delay)

if __name__ == "__main__":
    print("--- Standalone Motor Test ---")
    
    try:
        # Enable the motor driver (drive the pin LOW)
        en_pin.off()
        print("Motor Enabled. Holding torque should be active.")
        time.sleep(1)

        print("Spinning Clockwise...")
        dir_pin.on()
        spin_motor(steps=50000, delay=0.002) # 800 pulses
        
        time.sleep(1)

        print("Spinning Counter-Clockwise...")
        dir_pin.off()
        spin_motor(steps=50000, delay=0.002)

    except KeyboardInterrupt:
        print("\nTest stopped by user.")
    
    finally:
        # Disable the motor driver (drive the pin HIGH) to let it cool down
        en_pin.on()
        print("Motor Disabled. Test complete.")