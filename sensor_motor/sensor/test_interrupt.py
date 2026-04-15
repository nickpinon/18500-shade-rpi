#!/usr/bin/env python3
import time
from lsm6dsox.lsm6dsox import LSM6DSOX
from gpiozero import DigitalInputDevice

# Global counter
interrupt_count = 0

def on_interrupt():
    global interrupt_count
    interrupt_count += 1

def main():
    print("--- Hardware Interrupt Wire Test ---")
    
    print("1. Waking up LSM6DSOX...")
    # This calls your _init_sensor() function. 
    # If 0x0D, 0x03 is in there, the sensor will start firing the pin.
    imu = LSM6DSOX(bus_id=1) 
    
    print("2. Attaching listener to GPIO 4 (Physical Pin 7)...")
    drdy_pin = DigitalInputDevice(4, pull_up=False)
    drdy_pin.when_activated = on_interrupt
    
    print("\nListening for voltage spikes... (Press Ctrl+C to stop)")
    
    try:
        while True:
            # We MUST read the data to tell the sensor we received it.
            # If we don't read it, the sensor leaves the pin HIGH and it never triggers again.
            imu.read_accel()
            imu.read_gyro()
            
            # Print the total number of times the pin fired
            print(f"Total Interrupts Received: {interrupt_count}", end="\r", flush=True)
            
            # Sleep briefly to let the sensor generate new data
            time.sleep(0.05) 
            
    except KeyboardInterrupt:
        print("\n\nTest closed.")

if __name__ == "__main__":
    main()