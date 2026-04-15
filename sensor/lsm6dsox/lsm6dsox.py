import smbus2
import math
import time
import os
import json
import registers_dsox as reg

class LSM6DSOX:
    ADDR = 0x6A
    SENS_A_2G = 0.000061
    SENS_G_250 = 0.00875

    def __init__(self, bus_id=1, bias_file="imu_bias.json"):
        self.bus = smbus2.SMBus(bus_id)
        self.bias_file = bias_file
        self.accel_bias = [0.0, 0.0, 0.0]
        self.gyro_bias = [0.0, 0.0, 0.0]
        
        self.load_bias()
        self._init_sensor()

    def _init_sensor(self):
        if self.bus.read_byte_data(self.ADDR, reg.WHO_AM_I) != reg.WHO_AM_I_RSP:
            raise ConnectionError("LSM6DSOX not detected!")
        
        # Soft reset + Enable BDU & Auto-Increment (0x44)
        self.bus.write_byte_data(self.ADDR, reg.CTRL3_C, 0x01)
        time.sleep(0.1)
        self.bus.write_byte_data(self.ADDR, reg.CTRL3_C, 0x44)

        # Power on: 104Hz, 2g / 250dps
        self.bus.write_byte_data(self.ADDR, reg.CTRL1_XL, 0x40)
        self.bus.write_byte_data(self.ADDR, reg.CTRL2_G, 0x40)

    def _combine_bytes(self, low, high):
        val = (high << 8) | low
        return val - 65536 if val > 32767 else val

    def _read_16bit_vector(self, start_reg):
        """Attempts the faster I2C block read (6 bytes)."""
        try:
            # This is the 'old way' but using the correct I2C-specific command
            data = self.bus.read_i2c_block_data(self.ADDR, start_reg, 6)
            return [
                self._combine_bytes(data[0], data[1]),
                self._combine_bytes(data[2], data[3]),
                self._combine_bytes(data[4], data[5])
            ]
        except Exception:
            # Fallback to byte-by-byte if the block read fails again
            vals = [self.bus.read_byte_data(self.ADDR, start_reg + i) for i in range(6)]
            return [
                self._combine_bytes(vals[0], vals[1]),
                self._combine_bytes(vals[2], vals[3]),
                self._combine_bytes(vals[4], vals[5])
            ]

    def read_accel(self):
        raw = self._read_16bit_vector(reg.OUTX_L_A)
        return [(raw[i] - self.accel_bias[i]) * self.SENS_A_2G for i in range(3)]

    def read_gyro(self):
        raw = self._read_16bit_vector(reg.OUTX_L_G)
        return [(raw[i] - self.gyro_bias[i]) * self.SENS_G_250 * (math.pi / 180) for i in range(3)]

    # --- Bias Management ---
    def load_bias(self):
        if os.path.exists(self.bias_file):
            with open(self.bias_file, 'r') as f:
                data = json.load(f)
                self.accel_bias = data.get("accel", [0, 0, 0])
                self.gyro_bias = data.get("gyro", [0, 0, 0])

    def save_bias(self):
        with open(self.bias_file, 'w') as f:
            json.dump({"accel": self.accel_bias, "gyro": self.gyro_bias}, f, indent=4)