import time
import board
import busio
from adafruit_lsm9ds1 import LSM9DS1_I2C

# Initialize I2C
i2c = busio.I2C(board.SCL, board.SDA)
sensor = LSM9DS1_I2C(i2c)

# Read Data
while True:
    accel_x, accel_y, accel_z = sensor.acceleration
    gyro_x, gyro_y, gyro_z = sensor.gyro
    mag_x, mag_y, mag_z = sensor.magnetic
    print(f"Accel: {accel_x:.2f}, {accel_y:.2f}, {accel_z:.2f} m/s^2")
    time.sleep(0.1)
