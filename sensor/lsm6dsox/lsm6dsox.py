import smbus2
import math
import time
import registers_dsox as reg

class LSM6DSOX:
    ADDR = 0x6A  # Default for LSM6DSOX (change to 0x6B if SDO is high)

    # Sensitivities (at +/- 2g and +/- 250 dps)
    SENS_A_2G = 0.000061
    SENS_G_250 = 0.00875

    def __init__(self, bus_id=1):
        self.bus = smbus2.SMBus(bus_id)
        self.accel_bias = [0, 0, 0]
        self.gyro_bias = [0, 0, 0]
        self._init_sensor()

    def _init_sensor(self):
        # 1. Verify connection
        who_am_i = self.bus.read_byte_data(self.ADDR, reg.WHO_AM_I)
        if who_am_i != reg.WHO_AM_I_RSP:
            raise ConnectionError(f"LSM6DSOX not detected at {hex(self.ADDR)}!")
        
        # 2. Software Reset
        self.bus.write_byte_data(self.ADDR, reg.CTRL3_C, 0x01)
        time.sleep(0.1) # Wait for reboot

        # 3. Enable BDU (Block Data Update) and IF_INC (Auto-increment)
        # 0x44 sets Bit 6 (BDU) and Bit 2 (IF_INC)
        self.bus.write_byte_data(self.ADDR, reg.CTRL3_C, 0x44)

        # 4. Power on: 104Hz, +/- 2g / 250 dps
        self.bus.write_byte_data(self.ADDR, reg.CTRL1_XL, 0x40)
        self.bus.write_byte_data(self.ADDR, reg.CTRL2_G, 0x40)

        # 5. Verification: Read back to ensure registers were written
        check = self.bus.read_byte_data(self.ADDR, reg.CTRL1_XL)
        if check != 0x40:
            print(f"Warning: Accel config failed to write! Read: {hex(check)}")
    
    def _combine_bytes(self, low, high):
        val = (high << 8) | low
        return val - 65536 if val > 32767 else val

    def _read_16bit_vector(self, start_reg):
        # NO '| 0x80' here for LSM6DSOX
        data = self.bus.read_i2c_block_data(self.ADDR, start_reg, 6)
        return [
            self._combine_bytes(data[0], data[1]),
            self._combine_bytes(data[2], data[3]),
            self._combine_bytes(data[4], data[5])
        ]

    def read_accel(self):
        raw = self._read_16bit_vector(reg.OUTX_L_A)
        return [ (raw[i] - self.accel_bias[i]) * self.SENS_A_2G for i in range(3) ]

    def read_gyro(self):
        raw = self._read_16bit_vector(reg.OUTX_L_G)
        return [ (raw[i] - self.gyro_bias[i]) * self.SENS_G_250 * (math.pi / 180) for i in range(3) ]

    def calibrate(self, samples=256):
        print(f"Calibrating LSM6DSOX...")
        a_sums, g_sums = [0,0,0], [0,0,0]
        for _ in range(samples):
            a_raw = self._read_16bit_vector(reg.OUTX_L_A)
            g_raw = self._read_16bit_vector(reg.OUTX_L_G)
            for i in range(3):
                a_sums[i] += a_raw[i]
                g_sums[i] += g_raw[i]
            time.sleep(0.01)

        self.accel_bias = [a_sums[0]/samples, a_sums[1]/samples, (a_sums[2]/samples) - (1.0/self.SENS_A_2G)]
        self.gyro_bias = [g/samples for g in g_sums]
        print("Calibration complete.")