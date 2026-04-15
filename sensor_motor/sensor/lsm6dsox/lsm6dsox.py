import smbus2
import math
import time
import os
import json
try:
    from . import registers_dsox as reg
except ImportError:
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
        try:
            if self.bus.read_byte_data(self.ADDR, reg.WHO_AM_I) != reg.WHO_AM_I_RSP:
                raise ConnectionError("LSM6DSOX not detected!")
            self.bus.write_byte_data(self.ADDR, reg.CTRL3_C, 0x01) # Reset
            time.sleep(0.1)
            self.bus.write_byte_data(self.ADDR, reg.CTRL3_C, 0x44) # BDU + IF_INC
            self.bus.write_byte_data(self.ADDR, reg.CTRL1_XL, 0x40) # Accel ON (104Hz)
            self.bus.write_byte_data(self.ADDR, reg.CTRL2_G, 0x40)  # Gyro ON (104Hz)
            
            # --- NEW: Enable Hardware Interrupts ---
            # 0x0D is INT1_CTRL. 
            # 0x03 enables both Accel (0x01) and Gyro (0x02) Data Ready signals on the INT1 pin
            self.bus.write_byte_data(self.ADDR, 0x0D, 0x03) 
            
        except Exception as e:
            print(f"LSM6DSOX Init Failed: {e}")

    def _combine_bytes(self, low, high):
        val = (high << 8) | low
        return val - 65536 if val > 32767 else val

    def _read_16bit_vector(self, start_reg):
        """Uses the faster I2C block read."""
        data = self.bus.read_i2c_block_data(self.ADDR, start_reg, 6)
        return [self._combine_bytes(data[i*2], data[i*2+1]) for i in range(3)]

    def read_accel(self):
        raw = self._read_16bit_vector(reg.OUTX_L_A)
        return [(raw[i] - self.accel_bias[i]) * self.SENS_A_2G for i in range(3)]

    def read_gyro(self):
        raw = self._read_16bit_vector(reg.OUTX_L_G)
        return [(raw[i] - self.gyro_bias[i]) * self.SENS_G_250 * (math.pi / 180) for i in range(3)]

    def calibrate(self, samples=100):
        print("Calibrating IMU... Keep it level and still.")
        a_sums, g_sums = [0,0,0], [0,0,0]
        for _ in range(samples):
            a, g = self._read_16bit_vector(reg.OUTX_L_A), self._read_16bit_vector(reg.OUTX_L_G)
            for i in range(3):
                a_sums[i] += a[i]
                g_sums[i] += g[i]
            time.sleep(0.01)
        self.gyro_bias = [s/samples for s in g_sums]
        self.accel_bias = [a_sums[0]/samples, a_sums[1]/samples, (a_sums[2]/samples) - (1.0/self.SENS_A_2G)]
        self.save_bias()

    def load_bias(self):
        if os.path.exists(self.bias_file):
            with open(self.bias_file, 'r') as f:
                d = json.load(f)
                self.accel_bias, self.gyro_bias = d.get("accel", [0,0,0]), d.get("gyro", [0,0,0])

    def save_bias(self):
        with open(self.bias_file, 'w') as f:
            json.dump({"accel": self.accel_bias, "gyro": self.gyro_bias}, f, indent=4)