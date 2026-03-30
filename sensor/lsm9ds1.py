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
        self.accel_bias = [0, 0, 0]
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
    def _combine_bytes(self, low, high):
        val = (high << 8) | low
        return val - 65536 if val > 32767 else val
    def _read_16bit_vector(self, addr, start_reg):
        """Reads 6 bytes at once for X, Y, and Z."""
        data = self.bus.read_i2c_block_data(addr, start_reg | 0x80, 6)
        return [
            self._combine_bytes(data[0], data[1]),
            self._combine_bytes(data[2], data[3]),
            self._combine_bytes(data[4], data[5])
        ]
  
    def read_accel(self):
      # Ported from readAccel() in C++
      raw = self._read_16bit_vector(self.AG_ADDR, reg.OUT_X_L_XL)
      return [ 
          (raw[0] - self.accel_bias[0]) * self.SENS_A_2G,
          (raw[1] - self.accel_bias[1]) * self.SENS_A_2G,
          (raw[2] - self.accel_bias[2]) * self.SENS_A_2G
      ]
    def read_gyro(self):
        raw = self._read_16bit_vector(self.AG_ADDR, reg.OUT_X_L_G)
        return [x * self.SENS_G_245 * (math.pi / 180) for x in raw]  # Convert to radians/s
    
    def read_mag(self):
        raw = self._read_16bit_vector(self.M_ADDR, reg.OUT_X_L_M)
        return [x * self.SENS_M_4G for x in raw]
    
    def calibrate_accel(self, samples=32):
        print("Calibrating accelerometer... Please keep the device still.")
        ax_total, ay_total, az_total = 0, 0, 0
        for _ in range(samples):
            raw = self._read_16bit_vector(self.AG_ADDR, reg.OUT_X_L_XL)
            ax_total += raw[0]
            ay_total += raw[1]
            az_total += raw[2]
            time.sleep(0.02)
        
        self.accel_bias[0] = ax_total / samples
        self.accel_bias[1] = ay_total / samples
        self.accel_bias[2] = az_total / samples - (1 / self.SENS_A_2G)  # Subtract 1g for Z-axis

        print(f"Calibration complete. Biases: {self.accel_bias}")
    def _combine_bytes(self, low, high):
        val = (high << 8) | low
        return val - 65536 if val > 32767 else val
      
if __name__ == "__main__":
    imu = LSM9DS1()
    imu.calibrate_accel()
    
    
    while True:
        accel = imu.read_accel()
        gyro = imu.read_gyro()
        
        # Formatted output to avoid terminal ghosting
        output = (f"Accel(g) X:{accel[0]:>7.3f} Y:{accel[1]:>7.3f} Z:{accel[2]:>7.3f} | "
                  f"Gyro(rad/s) X:{gyro[0]:>7.3f} Y:{gyro[1]:>7.3f} Z:{gyro[2]:>7.3f}")
        print(output, end="\r", flush=True)
        time.sleep(0.1)
