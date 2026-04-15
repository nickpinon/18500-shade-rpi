#!/usr/bin/env python3
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lsm6dsox import LSM6DSOX
from mahony_fusion import MahonyFilter

def main():
    imu = LSM6DSOX(bus_id=1)
    imu.calibrate()
    
    # Use your existing Mahony implementation
    fusion = MahonyFilter(kp=0.5, ki=0.0)

    print("\n--- Orientation Active ---")
    while True:
        accel = imu.read_accel()
        gyro = imu.read_gyro()
        
        # Since you don't have the Magnetometer connected yet, 
        # use a dummy 'North' vector so the filter doesn't divide by zero.
        mag = [0, 1, 0] 

        roll, pitch, yaw = fusion.update(gyro, accel, mag)
        
        # Log raw data occasionally if still getting 0.00
        # print(f"Raw Accel: {accel}", end="\r") 

        output = f"Roll: {roll:>7.2f}° | Pitch: {pitch:>7.2f}° | Yaw: {yaw:>7.2f}°"
        print(output, end="\r", flush=True)
        time.sleep(0.02)

if __name__ == "__main__":
    main()