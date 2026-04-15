#!/usr/bin/env python3
import time
import os
import sys

# --- SENSOR CONFIGURATION ---
# Set to True for the new LSM6DSOX + LSM303AGR setup.
# Set to False to revert to the original LSM9DS1.
USE_NEW_BOARDS = True 

if USE_NEW_BOARDS:
    from lsm6dsox.lsm6dsox import LSM6DSOX
    from lsm303agr import LSM303AGR
    
    class IMU_DRIVER:
        def __init__(self, bus_id=1):
            # Paths are relative to where you run main.py
            self.imu = LSM6DSOX(bus_id=bus_id, bias_file="imu_bias.json")
            self.mag = LSM303AGR(bus_id=bus_id, bias_file="mag_bias.json")

        def read_accel(self): return self.imu.read_accel()
        def read_gyro(self):  return self.imu.read_gyro()
        def read_mag(self):   return self.mag.read_mag()

        def calibrate(self):
            print("Starting full system calibration...")
            self.imu.calibrate()
            self.mag.calibrate()
            print("Calibration complete. Offsets saved to JSON.")
else:
    from lsm9ds1 import LSM9DS1 as IMU_DRIVER

# Import the Mahony filter from your existing sensor folder
from mahony_fusion import MahonyFilter

def main():
    try:
        sensor = IMU_DRIVER(bus_id=1)
        fusion = MahonyFilter(kp=0.5, ki=0.01)

        print(f"\n--- {'Dual-Board' if USE_NEW_BOARDS else 'LSM9DS1'} Active ---")
        print("Press Ctrl+C to exit.")

        # Uncomment the next line if you want to force calibration on every start
        # sensor.calibrate()

        while True:
            # Data Acquisition
            accel = sensor.read_accel()
            gyro = sensor.read_gyro()
            mag = sensor.read_mag()

            # Orientation Fusion
            roll, pitch, yaw = fusion.update(gyro, accel, mag)

            # Clean Terminal Output
            print(f"Roll: {roll:>7.2f}° | Pitch: {pitch:>7.2f}° | Yaw: {yaw:>7.2f}°", end="\r", flush=True)

            # Maintain ~50Hz loop
            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"\nSystem Error: {e}")

if __name__ == "__main__":
    main()