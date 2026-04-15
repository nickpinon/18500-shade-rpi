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
    
    # Calibration Functions 
    def calibrate(self, samples=256):
    # Taken from LSM9DS1::calibrate() in C++

      print(f"Calibrating Accel & Gyro ({samples} samples)... Keep sensor level and still.")
      a_sums = [0, 0, 0]
      g_sums = [0, 0, 0]

      for _ in range(samples):
          # Read raw 16-bit values
          a_raw = self._read_16bit_vector(self.AG_ADDR, reg.OUT_X_L_XL)
          g_raw = self._read_16bit_vector(self.AG_ADDR, reg.OUT_X_L_G)
          
          for i in range(3):
              a_sums[i] += a_raw[i]
              g_sums[i] += g_raw[i]
          
          time.sleep(0.02)

      # Average the biases
      self.gyro_bias = [s / samples for s in g_sums]
      self.accel_bias[0] = a_sums[0] / samples
      self.accel_bias[1] = a_sums[1] / samples
      
      # Adjust Accel Z-axis for gravity: az - (1.0 / aRes)
      # This assumes the sensor is facing 'up' during calibration.
      self.accel_bias[2] = (a_sums[2] / samples) - (1.0 / self.SENS_A_2G)
      
      print("Calibration complete.")
      print(f"  Accel Biases (raw): {self.accel_bias}")
      print(f"  Gyro Biases (raw):  {self.gyro_bias}")
      
    def calibrate_mag(self, samples=256):
        print("Calibrating Magnnetometer. Rotate sensor in all orientations until complete.")
        # Initialize with the absolute limits of a 16-bit signed integer
        mag_min = [32767] * 3
        mag_max = [-32768] * 3

        for _ in range(samples):
            # Equivalent to readMag() in C++
            raw = self._read_16bit_vector(self.M_ADDR, reg.OUT_X_L_M)
            for i in range(3):
                # Equivalent to the C++ min/max if-statements
                if raw[i] < mag_min[i]: mag_min[i] = raw[i]
                if raw[i] > mag_max[i]: mag_max[i] = raw[i]
            time.sleep(0.05)

        # The Midpoint Formula: (Max + Min) / 2
        self.mag_bias = [(mag_max[i] + mag_min[i]) / 2 for i in range(3)]

# ---------------------------
# Threading/Interrupt Implementation 

import json 
import os
import threading
from gpiozero import DigitalInputDevice

class ThreadedIMU(LSM9DS1):
    def __init__(self, bus_id=1, interrupt_pin=17):
        super().__init__(bus_id)
        self.lock = threading.Lock()
        self.data = {"accel": [0,0,0], "gyro": [0,0,0], "mag": [0,0,0]}
        self.new_data_event = threading.Event()
        
        # 1. Pi 5 Interrupt Setup using gpiozero
        self.interrupt_device = DigitalInputDevice(interrupt_pin, pull_up=False)
        self.interrupt_device.when_activated = self._data_ready_callback

        # 2. Enable Data Ready (DRDY) on the LSM9DS1 hardware INT1 pin
        # 0x03 enables both Gyro and Accel Data Ready interrupts on INT1
        self.bus.write_byte_data(self.AG_ADDR, reg.INT1_CTRL, 0x03) 

    def _data_ready_callback(self):
        """Hardware interrupt triggers this callback."""
        with self.lock:
            self.data["accel"] = self.read_accel()
            self.data["gyro"] = self.read_gyro()
            self.data["mag"] = self.read_mag()
        self.new_data_event.set()

    def get_latest_fusion(self, fusion_engine):
        """Waits for hardware interrupt, then updates Mahony once."""
        self.new_data_event.wait() 
        with self.lock:
            orientation = fusion_engine.update(
                self.data["gyro"], self.data["accel"], self.data["mag"]
            )
        self.new_data_event.clear()
        return orientation

    # --- Bias Tuning & Saving Functions ---
    def save_calibration(self, filename="calibration.json"):
        data = {
            "accel_bias": self.accel_bias,
            "gyro_bias": getattr(self, 'gyro_bias', [0,0,0]),
            "mag_bias": getattr(self, 'mag_bias', [0,0,0])
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Calibration saved to {filename}. You can edit this file to tune biases.")

    def load_calibration(self, filename="calibration.json"):
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
                self.accel_bias = data.get("accel_bias", [0,0,0])
                self.gyro_bias = data.get("gyro_bias", [0,0,0])
                self.mag_bias = data.get("mag_bias", [0,0,0])
            print(f"Loaded tuned calibration from {filename}")
            return True
        return False
    
if __name__ == "__main__":
    imu = LSM9DS1()
    imu.calibrate()
    # imu.calibrate_mag()
    
    
    while True:
        a, g, m = imu.read_accel(), imu.read_gyro(), imu.read_mag()
        output = (f"A:({a[0]:>6.2f},{a[1]:>6.2f},{a[2]:>6.2f}) | "
                  f"G:({g[0]:>6.2f},{g[1]:>6.2f},{g[2]:>6.2f}) | "
                  f"M:({m[0]:>6.2f},{m[1]:>6.2f},{m[2]:>6.2f})")
        print(output, end="\r", flush=True)
        time.sleep(0.1)
