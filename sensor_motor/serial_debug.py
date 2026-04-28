import serial
import time

# Based on your RPi 5 port discovery
port = "/dev/ttyAMA0" 
baud = 115200

try:
    ser = serial.Serial(port, baud, timeout=0.2)
    print(f"Testing port {port}...")
    
    # A standard TMC2209 read request for the 'GCONF' register
    request = bytearray([0x05, 0x00, 0x00, 0x07])
    
    print("Sending request... (Ctrl+C to stop)")
    while True:
        ser.write(request)
        time.sleep(0.1)
        response = ser.read(12)
        
        if len(response) > 0:
            # If Received == Sent, it's just an echo (the chip is silent)
            # If Received > Sent, the chip is actually talking!
            print(f"Sent: {request.hex()} | Received: {response.hex()} ({len(response)} bytes)")
        else:
            print("Nothing received. Check power and TX/RX connections.")
        time.sleep(1)

except Exception as e:
    print(f"Error: {e}")