#!/usr/bin/env python3
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lsm6dsox import LSM6DSOX
from lsm303agr import LSM303AGR
from mahony_fusion import MahonyFilter

def main():
    # Initialize both sensors
    imu = LSM6DSOX(bus_id=1)
    mag_sensor = LSM303AGR(bus_id=1)
    
    # Calibrate (Keep level for IMU, Rotate for Mag)
    imu.calibrate()
    mag_sensor.calibrate()
    
    fusion = MahonyFilter(kp=5, ki=0.01, use_new_boards=True)

    print("\n--- 9-DOF Absolute Orientation Active ---")
    while True:
        accel = imu.read_accel()
        gyro = imu.read_gyro()
        mag = mag_sensor.read_mag()

        # Fusion now has real data for all 9 axes
        roll, pitch, yaw = fusion.update(gyro, accel, mag)
        
        output = f"Roll: {roll:>7.2f}° | Pitch: {pitch:>7.2f}° | Yaw: {yaw:>7.2f}°"
        print(output, end="\r", flush=True)
        time.sleep(0.02)

if __name__ == "__main__":
    main()