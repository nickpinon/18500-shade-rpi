import serial 
import time 
import lgpio 

class TMC2209: 
    def __init__(self, port="/dev/ttyAMA0", baud=115200, en_pin=21):
        self.ser = serial.Serial(port, baud,timeout=0.1)
        self.