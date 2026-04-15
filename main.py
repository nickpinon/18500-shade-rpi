#!/usr/bin/env python3
import time
from orientation_system import OrientationTracker

def central_main():
    # Initialize the tracker (Requires INT1 wired to GPIO 17)
    print("Initializing Sensor Subsystem...")
    tracker = OrientationTracker(interrupt_pin=17)
    
    # Start background interrupt processing
    tracker.start()
    print("Orientation tracking active in background.")

    try:
        # This represents the main loop of your entire RPi 5 system.
        # It can run at whatever speed it needs to (e.g., handling cameras, motors, UI).
        while True:
            # Instantly grab the latest calculated orientation
            roll, pitch, yaw = tracker.get_orientation()
            
            # Do main system logic here based on orientation...
            print(f"Main Loop -> R: {roll:>7.2f}° | P: {pitch:>7.2f}° | Y: {yaw:>7.2f}°", end="\r")
            
            # Main loop isn't bound by the sensor's 100Hz requirement anymore
            time.sleep(0.05) 
            
    except KeyboardInterrupt:
        print("\nShutting down central system...")
    finally:
        tracker.stop()

if __name__ == "__main__":
    central_main()