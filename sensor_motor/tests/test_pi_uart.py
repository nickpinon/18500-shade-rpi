import serial
import time

try:
    # Open the exact port we found earlier
    ser = serial.Serial("/dev/ttyAMA0", 115200, timeout=1)
    print("Port opened successfully.")
    
    test_message = b"HELLO_PI"
    ser.write(test_message)
    time.sleep(0.1)
    
    response = ser.read(ser.in_waiting)
    
    if response == test_message:
        print(f"SUCCESS: Pi UART is perfect! Received: {response}")
    elif len(response) > 0:
        print(f"WEIRD: Received garbled data: {response}")
    else:
        print("FAIL: Received 0 bytes. Your Pi's serial configuration is broken.")

except Exception as e:
    print(f"Error: {e}")