#!/usr/bin/env python3
import sys
import os
import time

# Allow importing from the parent sensor directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lsm6dsox import LSM6DSOX
from mahony_fusion import MahonyFilter

def main():
    imu = LSM6DSOX(bus_id=1)
    imu.calibrate()
    
    # Reusing your existing Mahony setup
    fusion = MahonyFilter(kp=0.5, ki=0.0)

    print("Running 6-DOF Orientation (No Magnetometer)")
    while True:
        accel = imu.read_accel()
        gyro = imu.read_gyro()
        mag = [0, 0, 0] # Placeholder for the missing Magnetometer

        roll, pitch, yaw = fusion.update(gyro, accel, mag)
        
        output = f"Roll: {roll:>7.2f}° | Pitch: {pitch:>7.2f}° | Yaw: {yaw:>7.2f}°"
        print(output, end="\r", flush=True)
        time.sleep(0.05)

if __name__ == "__main__":
    main()