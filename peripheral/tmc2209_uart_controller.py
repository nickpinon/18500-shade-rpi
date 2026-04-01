import time
from tmc2209 import TMC_2209

class UARTMotorController:
    def __init__(self, serial_port="/dev/ttyAMA0", en_pin=21, step_pin=16, dir_pin=20):
        print(f"Initializing TMC2209 on {serial_port}...")
        
        # The library automatically handles the Pi 5's lgpio backend
        # and filters out the UART "echo" caused by the single-wire setup.
        self.tmc = TMC_2209(
            pin_en=en_pin,
            pin_step=step_pin,
            pin_dir=dir_pin,
            baudrate=115200,
            serialport=serial_port
        )
        
        self._configure_driver()

    def _configure_driver(self):
        """Sets the software-defined hardware limits."""
        self.tmc.set_motor_enabled(True)
        
        # 1/16 microstepping is standard for smooth, quiet operation
        self.tmc.set_microstepping_res(16)
        
        # Set current to 800mA (No screwdriver required!)
        self.tmc.set_current(800) 
        
        # Enable StealthChop for dead-silent running
        self.tmc.set_stealth_chop(True) 
        print("Driver Configured: 800mA, 1/16 Step, StealthChop Active.")

    def set_velocity(self, speed):
        """
        Sets the VACTUAL register. 
        Speed is a signed 24-bit integer. Positive = CW, Negative = CCW.
        Because of the 51:1 gearbox, you need high values here (e.g., 50000+).
        """
        self.tmc.set_vactual(speed)

    def stop(self):
        """Safely stops the motor and cuts power to the coils."""
        self.tmc.set_vactual(0)
        self.tmc.set_motor_enabled(False)
        print("Motor stopped and disabled.")

# --- Test Execution Block ---
if __name__ == "__main__":
    # Create the controller instance
    motor = UARTMotorController()

    try:
        print("\nStarting Velocity Test...")
        # Start at a decent speed. Adjust this up or down to see the effect
        # on your 51:1 output shaft.
        test_speed = 150000 
        
        print(f"Spinning Forward at {test_speed}...")
        motor.set_velocity(test_speed)
        time.sleep(4)  # Let it run for 4 seconds

        print(f"Reversing at {-test_speed}...")
        motor.set_velocity(-test_speed)
        time.sleep(4)

        print("Decelerating to a stop...")
        motor.set_velocity(0)
        time.sleep(1)

    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    
    finally:
        motor.stop()