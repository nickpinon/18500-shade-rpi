import smbus2
import math
import time
import registers_dsox as reg

class LSM6DSOX:
    ADDR = 0x6A

    SENS_A_2G = 0.000061
    SENS_G_250 = 0.00875

    def __init__(self, bus_id=1):
        self.bus = smbus2.SMBus(bus_id)
        self.accel_bias = [0, 0, 0]
        self.gyro_bias = [0, 0, 0]
        self._init_sensor()

    def _init_sensor(self):
        # Verify connection
        if self.bus.read_byte_data(self.ADDR, reg.WHO_AM_I) != reg.WHO_AM_I_RSP:
            raise ConnectionError("LSM6DSOX not detected!")
        
        # Soft reset
        self.bus.write_byte_data(self.ADDR, reg.CTRL3_C, 0x01)
        time.sleep(0.1)

        # Set BDU (Block Data Update) to ensure high/low bytes match
        # and IF_INC for auto-increment (though we'll read manually to be safe)
        self.bus.write_byte_data(self.ADDR, reg.CTRL3_C, 0x44)

        # Power on Accel (104Hz, 2g) and Gyro (104Hz, 250dps)
        self.bus.write_byte_data(self.ADDR, reg.CTRL1_XL, 0x40)
        self.bus.write_byte_data(self.ADDR, reg.CTRL2_G, 0x40)

    def _combine_bytes(self, low, high):
        val = (high << 8) | low
        return val - 65536 if val > 32767 else val

    def _read_16bit_vector(self, start_reg):
        """Replaced block read with individual reads for Pi 5 compatibility."""
        vals = []
        for i in range(6):
            vals.append(self.bus.read_byte_data(self.ADDR, start_reg + i))
        
        return [
            self._combine_bytes(vals[0], vals[1]), # X
            self._combine_bytes(vals[2], vals[3]), # Y
            self._combine_bytes(vals[4], vals[5])  # Z
        ]

    def read_accel(self):
        raw = self._read_16bit_vector(reg.OUTX_L_A)
        return [(raw[i] - self.accel_bias[i]) * self.SENS_A_2G for i in range(3)]

    def read_gyro(self):
        raw = self._read_16bit_vector(reg.OUTX_L_G)
        return [(raw[i] - self.gyro_bias[i]) * self.SENS_G_250 * (math.pi / 180) for i in range(3)]

    def calibrate(self, samples=100):
        print(f"Calibrating... Keep sensor level and still.")
        a_sums = [0, 0, 0]
        g_sums = [0, 0, 0]
        for _ in range(samples):
            a = self._read_16bit_vector(reg.OUTX_L_A)
            g = self._read_16bit_vector(reg.OUTX_L_G)
            for i in range(3):
                a_sums[i] += a[i]
                g_sums[i] += g[i]
            time.sleep(0.01)
        
        self.gyro_bias = [s / samples for s in g_sums]
        self.accel_bias = [
            a_sums[0] / samples,
            a_sums[1] / samples,
            (a_sums[2] / samples) - (1.0 / self.SENS_A_2G)
        ]
        print("Calibration Done.")