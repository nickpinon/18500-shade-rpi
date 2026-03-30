#!/usr/bin/env python3

"""
Inspired by LSM9DS1_Basic_I2C.ino from Adafruit's LSM9DS1 library:
https://github.com/sparkfun/SparkFun_LSM9DS1_Arduino_Library/blob/master/examples/LSM9DS1_Basic_I2C/LSM9DS1_Basic_I2C.ino

Referenced this repo for Mahony AHRS implementation:
https://github.com/jremington/LSM9DS1-AHRS/blob/main/LSM9DS1_cal_data/LSM9DS1_cal_data.ino 
"""

import smbus2
import math
import time
import registers as reg

class LSM9DS1:
    AG_ADDR = 0x6B
    M_ADDR  = 0x1E

    # Exact constants from SparkFunLSM9DS1.cpp
    SENS_A_2G = 0.000061
    SENS_G_245 = 0.00875
    SENS_M_4G = 0.00014

    def __init__(self, bus_id=1):
        self.bus = smbus2.SMBus(bus_id)
        self._init_sensor()

    def _init_sensor(self):
        # Verify connection (Logic from begin() in C++)
        if self.bus.read_byte_data(self.AG_ADDR, reg.WHO_AM_I_XG) != reg.WHO_AM_I_AG_RSP:
            raise ConnectionError("Accel/Gyro not detected!")
        
        # Power on Gyro & Accel (Standard ODR 119Hz)
        self.bus.write_byte_data(self.AG_ADDR, reg.CTRL_REG1_G, 0x60)
        self.bus.write_byte_data(self.AG_ADDR, reg.CTRL_REG6_XL, 0x60)
        # Power on Mag (Continuous conversion)
        self.bus.write_byte_data(self.M_ADDR, reg.CTRL_REG3_M, 0x00)

    def read_accel(self):
        # Ported from readAccel() in C++
        data = self.bus.read_i2c_block_data(self.AG_ADDR, reg.OUT_X_L_XL | 0x80, 6)
        # Combining bytes: (temp[1] << 8) | temp[0]
        ax = self._combine_bytes(data[0], data[1])
        ay = self._combine_bytes(data[2], data[3])
        az = self._combine_bytes(data[4], data[5])
        return [ax * self.SENS_A_2G, ay * self.SENS_A_2G, az * self.SENS_A_2G]

    def _combine_bytes(self, low, high):
        val = (high << 8) | low
        return val - 65536 if val > 32767 else val

if __name__ == "__main__":
    imu = LSM9DS1()
    while True:
        print(f"Accel: {imu.read_accel()}", end="\r")
        time.sleep(0.1)