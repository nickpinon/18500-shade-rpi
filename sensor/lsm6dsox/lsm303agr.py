import smbus2
import time

class LSM303AGR:
    # I2C Addresses
    MAG_ADDR = 0x1E  # Magnetometer
    # Note: We ignore 0x19 (Accel) since we use the LSM6DSOX for that

    def __init__(self, bus_id=1):
        self.bus = smbus2.SMBus(bus_id)
        # Calibration offsets (Hard-iron)
        self.mag_bias = [0, 0, 0]
        self._init_mag()

    def _init_mag(self):
        # 1. Verify connection (WHO_AM_I is at 0x4F for the Mag)
        if self.bus.read_byte_data(self.MAG_ADDR, 0x4F) != 0x40:
            raise ConnectionError("LSM303AGR Magnetometer not detected at 0x1E!")

        # 2. CFG_REG_A_M (0x60): 10Hz, Continuous conversion mode
        self.bus.write_byte_data(self.MAG_ADDR, 0x60, 0x00)
        
        # 3. CFG_REG_C_M (0x62): Enable BDU (Block Data Update)
        # This prevents reading high/low bytes from different samples
        self.bus.write_byte_data(self.MAG_ADDR, 0x62, 0x10)

    def _combine_bytes(self, low, high):
        val = (high << 8) | low
        return val - 65536 if val > 32767 else val

    def read_mag(self):
        """Read 6 bytes of mag data starting at 0x68."""
        vals = []
        for i in range(6):
            vals.append(self.bus.read_byte_data(self.MAG_ADDR, 0x68 + i))
        
        # LSM303AGR sensitivity is fixed at 1.5 mGauss / LSB
        raw = [
            self._combine_bytes(vals[0], vals[1]), # X
            self._combine_bytes(vals[2], vals[3]), # Y
            self._combine_bytes(vals[4], vals[5])  # Z
        ]
        
        # Apply bias and convert to Gauss
        return [(raw[i] - self.mag_bias[i]) * 0.0015 for i in range(3)]

    def calibrate(self, samples=200):
        """Rotate the sensor in a figure-8 during this time!"""
        print("Calibrating Magnetometer... ROTATE SENSOR NOW!")
        mag_x, mag_y, mag_z = [], [], []
        
        for _ in range(samples):
            m = self.read_mag()
            mag_x.append(m[0] / 0.0015) # Work in raw units for bias calc
            mag_y.append(m[1] / 0.0015)
            mag_z.append(m[2] / 0.0015)
            time.sleep(0.02)
            
        self.mag_bias = [
            (max(mag_x) + min(mag_x)) / 2,
            (max(mag_y) + min(mag_y)) / 2,
            (max(mag_z) + min(mag_z)) / 2
        ]
        print(f"Mag Calibration Done. Offsets: {self.mag_bias}")