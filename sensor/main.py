#!/usr/bin/env python3
from lsm9ds1 import LSM9DS1
from mahony_fusion import MahonyFilter
import time

def main():
    imu = LSM9DS1()
    imu.calibrate()
    imu.calibrate_mag()
    fusion = MahonyFilter(kp=0.5, ki=0.0)

    print("Attempting AHRS")
    print("Coordinates: Roll(X), Pitch(Y), Yaw(Z) in degrees")



    while True:
        accel = imu.read_accel()
        gyro = imu.read_gyro()
        mag = imu.read_mag()
        roll, pitch, yaw = fusion.update(gyro, accel, mag)
        output = f"Roll: {roll:>7.2f}° | Pitch: {pitch:>7.2f}° | Yaw: {yaw:>7.2f}°"
        print(output, end="\r", flush=True)
        time.sleep(0.1)

if __name__ == "__main__":
    main()