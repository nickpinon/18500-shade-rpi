# Save as debug_raw.py
import smbus2
import time

bus = smbus2.SMBus(1)
ADDR = 0x6A

# Minimal Init
bus.write_byte_data(ADDR, 0x10, 0x40) # Accel ON
bus.write_byte_data(ADDR, 0x11, 0x40) # Gyro ON
bus.write_byte_data(ADDR, 0x12, 0x44) # BDU + IF_INC

print("Reading RAW Accel X-axis bytes. Shake the sensor!")
while True:
    # Read the 2 bytes of the X-axis accelerometer (0x28 and 0x29)
    low = bus.read_byte_data(ADDR, 0x28)
    high = bus.read_byte_data(ADDR, 0x29)
    print(f"Raw Hex: {hex(high)}{hex(low)} | Int: {(high << 8) | low}", end="\r")
    time.sleep(0.1)