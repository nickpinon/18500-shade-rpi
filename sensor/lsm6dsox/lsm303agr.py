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
        self.bus.write_byte_data(self.MAG_ADDR, 0x60, 0x0C)  # Continuous mode, 10Hz ODR
        self.bus.write_byte_data(self.MAG_ADDR, 0x62, 0x10)  # BDU enabled

    def _combine_bytes(self, low, high):
        val = (high << 8) | low
        return val - 65536 if val > 32767 else val

    def read_mag(self):
        data = self.bus.read_i2c_block_data(self.MAG_ADDR, 0x68 | 0x80, 6)
        raw = [self._combine_bytes(data[i*2], data[i*2+1]) for i in range(3)]

        # Apply hard-iron bias and convert to Gauss
        mx = (raw[0] - self.mag_bias[0]) * 0.0015
        my = (raw[1] - self.mag_bias[1]) * 0.0015
        mz = (raw[2] - self.mag_bias[2]) * 0.0015
        return [mx, my, mz]

    def calibrate(self, duration_seconds=15):
        """
        Hard-iron calibration using min/max capture over a timed window.

        The original version used only 200 samples at 20ms = 4 seconds, which
        is not enough time to rotate the sensor through all orientations. This
        also stored biases as raw counts but the division by 0.0015 could
        introduce unit confusion. Now we:
          - Run for a user-controlled duration (default 15s) so you have time
            to fully rotate through all axes
          - Work entirely in raw counts (bias is subtracted before conversion)
          - Print progress so you know how much time remains
        """
        print(f"Calibrating Magnetometer for {duration_seconds} seconds...")
        print(">>> SLOWLY rotate the sensor in a full figure-8 / all orientations <<<")

        mag_min = [32767,  32767,  32767]
        mag_max = [-32768, -32768, -32768]

        start = time.time()
        samples = 0
        while time.time() - start < duration_seconds:
            data = self.bus.read_i2c_block_data(self.MAG_ADDR, 0x68 | 0x80, 6)
            raw = [self._combine_bytes(data[i*2], data[i*2+1]) for i in range(3)]
            for i in range(3):
                if raw[i] < mag_min[i]: mag_min[i] = raw[i]
                if raw[i] > mag_max[i]: mag_max[i] = raw[i]
            samples += 1
            elapsed = time.time() - start
            remaining = duration_seconds - elapsed
            print(f"  {remaining:4.1f}s left | "
                  f"X:[{mag_min[0]:6d},{mag_max[0]:6d}] "
                  f"Y:[{mag_min[1]:6d},{mag_max[1]:6d}] "
                  f"Z:[{mag_min[2]:6d},{mag_max[2]:6d}]",
                  end="\r")
            time.sleep(0.02)

        # Hard-iron offset = midpoint of the min/max range per axis
        # Stored as raw counts — subtracted before Gauss conversion in read_mag()
        self.mag_bias = [
            (mag_max[0] + mag_min[0]) / 2,
            (mag_max[1] + mag_min[1]) / 2,
            (mag_max[2] + mag_min[2]) / 2,
        ]
        self.save_bias()
        print(f"\nCalibration complete ({samples} samples).")
        print(f"  Hard-iron bias (raw counts): {[round(b) for b in self.mag_bias]}")
        spread = [mag_max[i] - mag_min[i] for i in range(3)]
        print(f"  Axis spread (raw counts):    {spread}")
        if min(spread) < 200:
            print("  WARNING: One or more axes have very small spread. "
                  "Try rotating more aggressively, or the sensor may be "
                  "obstructed by nearby ferromagnetic material.")

    def load_bias(self):
        if os.path.exists(self.bias_file):
            with open(self.bias_file, 'r') as f:
                self.mag_bias = json.load(f).get("mag", [0, 0, 0])

    def save_bias(self):
        with open(self.bias_file, 'w') as f:
            json.dump({"mag": self.mag_bias}, f, indent=4)