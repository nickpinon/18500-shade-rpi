import sys
import os
import time
import csv
import curses
import lgpio

# Add the parent directory (sensor_motor) to the Python path
# so we can import the orientation sensor module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sensor.orientation_system import OrientationTracker

# --- Motor Configuration ---
VERT_STEP_PIN = 12
VERT_DIR_PIN  = 13
VERT_EN_PIN   = 16

HORIZ_STEP_PIN = 17
HORIZ_DIR_PIN  = 27
HORIZ_EN_PIN   = 22

STEP_COUNT = 50       # How many steps to move per keystroke
STEP_DELAY = 0.001    # Speed of the step (0.001 = 500Hz). Increase if motor stalls.
LOG_FILE = "imu_motor_test_data.csv"

def init_motors():
    """Initializes the GPIO chip and configures motor pins as outputs."""
    chip = lgpio.gpiochip_open(0)
    
    # Claim Vertical Pins
    lgpio.gpio_claim_output(chip, VERT_STEP_PIN, 0)
    lgpio.gpio_claim_output(chip, VERT_DIR_PIN, 0)
    lgpio.gpio_claim_output(chip, VERT_EN_PIN, 0) # 0 = Enable TMC2209
    
    # Claim Horizontal Pins
    lgpio.gpio_claim_output(chip, HORIZ_STEP_PIN, 0)
    lgpio.gpio_claim_output(chip, HORIZ_DIR_PIN, 0)
    lgpio.gpio_claim_output(chip, HORIZ_EN_PIN, 0) # 0 = Enable TMC2209

    return chip

def disable_motors(chip):
    """Turns off the TMC2209 drivers to prevent overheating."""
    try:
        lgpio.gpio_write(chip, VERT_EN_PIN, 1)  # 1 = Disable
        lgpio.gpio_write(chip, HORIZ_EN_PIN, 1) # 1 = Disable
        lgpio.gpiochip_close(chip)
    except Exception:
        pass

def step_motor(chip, step_pin, dir_pin, forward, steps):
    """Directly pulses the specified motor pins."""
    # Set Direction
    lgpio.gpio_write(chip, dir_pin, 1 if forward else 0)
    
    # Pulse Step Pin
    for _ in range(steps):
        lgpio.gpio_write(chip, step_pin, 1)
        time.sleep(STEP_DELAY)
        lgpio.gpio_write(chip, step_pin, 0)
        time.sleep(STEP_DELAY)

def main(stdscr):
    # Setup Curses terminal for SSH control
    stdscr.nodelay(True)  # Don't block waiting for input
    stdscr.clear()
    
    # Initialize Hardware
    stdscr.addstr(0, 0, "Initializing Hardware... Please wait.")
    stdscr.refresh()
    
    # Setup Motors directly
    gpio_chip = init_motors()
    
    # Setup IMU
    tracker = OrientationTracker(interrupt_pin=4) 
    tracker.start()
    
    time.sleep(1) # Let the filter warm up
    
    # Setup CSV Logging
    csv_file = open(LOG_FILE, mode='w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["Timestamp", "Command", "Roll", "Pitch", "Yaw"])
    
    is_recording = False
    start_time = time.time()

    try:
        while True:
            stdscr.clear()
            
            # Read Sensor Data
            roll, pitch, yaw = tracker.get_orientation()
            current_time = time.time() - start_time
            
            # Draw UI
            stdscr.addstr(0, 0, "=== Standalone Motor & IMU Calibration Test ===")
            stdscr.addstr(2, 0, "Controls: W/S (Tilt Up/Down), A/D (Pan Left/Right)")
            stdscr.addstr(3, 0, "          R (Toggle Recording), Q (Quit)")
            
            stdscr.addstr(5, 0, f"IMU Data -> Roll: {roll:>7.2f}° | Pitch: {pitch:>7.2f}° | Yaw: {yaw:>7.2f}°")
            
            rec_status = "ON (Writing to CSV)" if is_recording else "OFF"
            stdscr.addstr(7, 0, f"Recording Status: {rec_status}")

            # Handle Keystrokes
            key = stdscr.getch()
            command = "IDLE"
            
            if key != -1:
                char = chr(key).lower()
                if char == 'q':
                    break
                elif char == 'r':
                    is_recording = not is_recording
                elif char == 'w': # Tilt Up
                    step_motor(gpio_chip, VERT_STEP_PIN, VERT_DIR_PIN, True, STEP_COUNT)
                    command = "TILT_UP"
                elif char == 's': # Tilt Down
                    step_motor(gpio_chip, VERT_STEP_PIN, VERT_DIR_PIN, False, STEP_COUNT)
                    command = "TILT_DOWN"
                elif char == 'a': # Pan Left
                    step_motor(gpio_chip, HORIZ_STEP_PIN, HORIZ_DIR_PIN, False, STEP_COUNT)
                    command = "PAN_LEFT"
                elif char == 'd': # Pan Right
                    step_motor(gpio_chip, HORIZ_STEP_PIN, HORIZ_DIR_PIN, True, STEP_COUNT)
                    command = "PAN_RIGHT"

            # Log Data
            if is_recording:
                csv_writer.writerow([f"{current_time:.3f}", command, f"{roll:.2f}", f"{pitch:.2f}", f"{yaw:.2f}"])

            stdscr.refresh()
            time.sleep(0.05) # ~20Hz UI update rate

    except Exception as e:
        # Print error details to a file since curses will swallow standard print outputs
        with open("error_log.txt", "w") as f:
            f.write(str(e))
    finally:
        # Cleanup everything safely
        csv_file.close()
        tracker.stop()
        disable_motors(gpio_chip)
        
        # Reset terminal properly
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()
        print(f"Test finished. Data saved to {LOG_FILE}")

if __name__ == "__main__":
    # Wrap in curses to handle terminal state safely even if the script crashes
    curses.wrapper(main)