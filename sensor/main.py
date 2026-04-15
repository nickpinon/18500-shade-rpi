#!/usr/bin/env python3
import time
import os
import sys

# --- SENSOR CONFIGURATION ---
# Set to True to use the new LSM6DSOX + LSM303AGR boards.
# Set to False to revert to the original LSM9DS1.
USE_NEW_BOARDS = True 

if USE_NEW_BOARDS:
    # Import from the new subfolder
    from lsm6dsox.lsm6dsox import LSM6DSOX
    from lsm6dsox.lsm303agr import LSM303AGR
    
    class IMU_DRIVER:
        """Wrapper to make dual boards look like a single 9-DOF sensor."""
        def __init__(self, bus_id=1):
            # These classes handle loading/saving their own .json bias files
            self.imu = LSM6DSOX(bus_id=bus_id, bias_file="imu_bias.json")
            self.mag = LSM303AGR(bus_id=bus_id, bias_file="mag_bias.json")

        def read_accel(self):
            return self.imu.read_accel()

        def read_gyro(self):
            return self.imu.read_gyro()

        def read_mag(self):
            return self.mag.read_mag()

        def calibrate(self):
            # Note: This will overwrite your .json bias files
            self.imu.calibrate()
            self.mag.calibrate()
else:
    # Use the original driver
    from lsm9ds1 import LSM9DS1 as IMU_DRIVER

# Import the shared fusion filter
from mahony_fusion import MahonyFilter

def main():
    try:
        # Initialize the chosen driver
        sensor = IMU_DRIVER(bus_id=1)
        
        # Initialize the Mahony filter (kp and ki can be tuned for responsiveness)
        fusion = MahonyFilter(kp=0.5, ki=0.01)

        print("\n--- Orientation System Active ---")
        print("Press Ctrl+C to stop.")

        # Optional: Uncomment to run a fresh calibration on startup
        # sensor.calibrate()

        while True:
            # 1. Read raw data from the wrapper
            accel = sensor.read_accel()
            gyro = sensor.read_gyro()
            mag = sensor.read_mag()

            # 2. Update the orientation filter
            # Returns Euler angles in degrees
            roll, pitch, yaw = fusion.update(gyro, accel, mag)

            # 3. Output the results
            output = f"Roll: {roll:>7.2f}° | Pitch: {pitch:>7.2f}° | Yaw: {yaw:>7.2f}°"
            print(output, end="\r", flush=True)

            # 4. Control loop frequency (~50Hz)
            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nStopping sensor integration...")
    except Exception as e:
        print(f"\nHardware Error: {e}")

if __name__ == "__main__":
    main()