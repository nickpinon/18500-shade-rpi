#!/usr/bin/env python3
import sys
import os
import time
import math

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
    
    fusion = MahonyFilter(kp=2.0, ki=0.01, use_new_boards=True)

    print("\n--- Warming up AHRS Filter ---")
    # Temporarily crank up the proportional gain
    fusion.kp = 10.0 
    
    # Rapidly pump data into the filter to force convergence
    for _ in range(500):
        accel = imu.read_accel()
        gyro = imu.read_gyro()
        mag = mag_sensor.read_mag()
        fusion.update(gyro, accel, mag)
        time.sleep(0.002) # Very short delay
        
    # Return gain to normal for smooth, noise-resistant operation
    fusion.kp = 2.0 

    print("\n--- 9-DOF Absolute Orientation Active ---")
    while True:
        accel = imu.read_accel()
        gyro = imu.read_gyro()
        # Inside your while loop in lsm6dsox/main.py
        mag = mag_sensor.read_mag()
        # Calculate a simple 2D heading from the mag alone (in degrees)
        # mag_heading = math.degrees(math.atan2(mag[1], mag[0]))
        # mag_magnitude = math.sqrt(mag[0]**2 + mag[1]**2 + mag[2]**2)

        # print(f"Mag Heading: {mag_heading:>7.2f} | Strength: {mag_magnitude:>7.2f}", end="\r")

        # Fusion now has real data for all 9 axes
        # Fusion now has real data for all 9 axes
        roll, pitch, yaw = fusion.update(gyro, accel, mag)
        
        # Apply Magnetic Declination for Pittsburgh (8.5 Degrees West)
        DECLINATION_OFFSET = -8.5 
        
        true_yaw = yaw + DECLINATION_OFFSET
        
        # Keep it cleanly within a 0-360 degree format (optional but recommended)
        if true_yaw < 0:
            true_yaw += 360.0
        elif true_yaw >= 360.0:
            true_yaw -= 360.0
        
        output = f"Roll: {roll:>7.2f}° | Pitch: {pitch:>7.2f}° | Yaw: {true_yaw:>7.2f}°"
        print(output, end="\r", flush=True)
        time.sleep(0.01)

if __name__ == "__main__":
    main()