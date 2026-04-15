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
    from lsm6dsox.lsm303agr import LSM303AGR
    
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
        
        # --- FILTER TUNING ---
        # ki=0.0 prevents integral windup (rubber-banding / slow settling)
        # kp=5.0 gives a snappy response to the magnetometer
        fusion = MahonyFilter(kp=5.0, ki=0.0, use_new_boards=USE_NEW_BOARDS)

        print(f"\n--- {'Dual-Board' if USE_NEW_BOARDS else 'LSM9DS1'} Active ---")

        # Uncomment to force calibration on every start
        # sensor.calibrate()

        # --- WARM-UP PHASE ---
        print("\n--- Warming up AHRS Filter ---")
        fusion.kp = 10.0 # Temporarily high gain to force instant convergence
        for _ in range(250):
            accel = sensor.read_accel()
            gyro = sensor.read_gyro()
            mag = sensor.read_mag()
            fusion.update(gyro, accel, mag)
            time.sleep(0.002) # Rapid fire updates
            
        fusion.kp = 5.0 # Return to standard operation
        print("--- Warmup Complete. Press Ctrl+C to exit. ---")

        while True:
            # Data Acquisition
            accel = sensor.read_accel()
            gyro = sensor.read_gyro()
            mag = sensor.read_mag()

            # Orientation Fusion
            roll, pitch, yaw = fusion.update(gyro, accel, mag)

            # --- YAW CORRECTIONS ---
            # 1. Local magnetic declination (~8.5 degrees West)
            DECLINATION = -8.5
            
            # 2. Physical Board Mount Offset (to fix the -60 degree offset)
            BOARD_MOUNT_OFFSET = 60.0 
            
            # Apply corrections for True Yaw
            true_yaw = yaw + DECLINATION + BOARD_MOUNT_OFFSET
            
            # Normalize to keep output strictly between 0 and 360 degrees
            true_yaw = true_yaw % 360.0

            # Clean Terminal Output (Matches lsm6dsox/main.py formatting)
            output = f"Roll: {roll:>7.2f}° | Pitch: {pitch:>7.2f}° | Yaw: {true_yaw:>7.2f}°"
            print(output, end="\r", flush=True)

            # Maintain ~50Hz loop
            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"\nSystem Error: {e}")

if __name__ == "__main__":
    main()