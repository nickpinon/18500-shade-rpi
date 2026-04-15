import smbus2
import time
import json
import os

class LSM303AGR:
    MAG_ADDR = 0x1E

    def __init__(self, bus_id=1, bias_file="mag_bias.json"):
        self.bus = smbus2.SMBus(bus_id)
        self.bias_file = bias_file
        self.mag_bias = [0, 0, 0]
        self.load_bias()
        self._init_mag()

    def _init_mag(self):
        self.bus.write_byte_data(self.MAG_ADDR, 0x60, 0x00) # 10Hz Continuous
        self.bus.write_byte_data(self.MAG_ADDR, 0x62, 0x10) # BDU

    def _combine_bytes(self, low, high):
        val = (high << 8) | low
        return val - 65536 if val > 32767 else val

    def read_mag(self):
        data = self.bus.read_i2c_block_data(self.MAG_ADDR, 0x68, 6)
        raw = [self._combine_bytes(data[i*2], data[i*2+1]) for i in range(3)]
        
        # Apply bias and convert to Gauss
        mx = (raw[0] - self.mag_bias[0]) * 0.0015
        my = (raw[1] - self.mag_bias[1]) * 0.0015
        mz = (raw[2] - self.mag_bias[2]) * 0.0015

        return [mx, my, mz]

    def calibrate(self, samples=200):
        print("Calibrating Mag... ROTATE IN FIGURE-8!")
        xs, ys, zs = [], [], []
        for _ in range(samples):
            m = self.read_mag()
            xs.append(m[0]/0.0015); ys.append(m[1]/0.0015); zs.append(m[2]/0.0015)
            time.sleep(0.02)
        self.mag_bias = [(max(xs)+min(xs))/2, (max(ys)+min(ys))/2, (max(zs)+min(zs))/2]
        self.save_bias()

    def load_bias(self):
        if os.path.exists(self.bias_file):
            with open(self.bias_file, 'r') as f:
                self.mag_bias = json.load(f).get("mag", [0,0,0])

    def save_bias(self):
        with open(self.bias_file, 'w') as f:
            json.dump({"mag": self.mag_bias}, f, indent=4)