"""
Integrator Script

Coordinates:
- Sun sensor emulator (alpha, beta, error_code)
- User detection (error_x, error_y)
- Manual control (app input → motor commands)

NOTE: GPIO motor control will be added later.
"""

from .user_detection.userDetection import init_user_detection, get_user_errors, shutdown_user_detection
from .sun_location import calculate_sun_direction

# from ..sun_sensor import get_sun_sensor_data

import time
from .ble.ble_server import state, state_lock, run as ble_run
import threading
import asyncio
from .motor import motor
from .sensor.main import OrientationTracker


# Configuration
# (speed) = LOOP_HZ × steps_per_loop
LOOP_HZ = 10  # main loop frequency (Hz)


# === State ===
running = True


# Sun Sensor Interface
def get_sun_sensor_data():
    """
    @brief Retrieve sun sensor data

    @return alpha (float): horizontal angle
    @return beta (float): vertical angle
    @return error_code (int): sensor status
    """
    # Use GPS + time received from iOS over BLE and compute on the Pi.
    with state_lock:
        latitude = state.target_latitude
        longitude = state.target_longitude
        timestamp = state.target_timestamp

    sun = calculate_sun_direction(latitude, longitude, timestamp)
    # update_sun_status(sun.azimuth_deg, sun.elevation_deg, sun.source)
    alpha = sun.azimuth_deg
    beta = sun.elevation_deg
    # 0 = exact BLE location, 1 = fallback default location
    error_code = 0 if sun.source == "ble_location" else 1
    # return alpha, beta, error_code
    return 0, 0, 0


# Motor Command Interface
def send_motor_commands(error_x, error_y):
    """
    @brief Send commands to motors for pan (horizontal) and tilt (vertical)

    error_x controls horizontal panning
    error_y controls vertical tilting
    """

    moved = False

    # Horizontal (pan) with smooth scaling
    if error_x is not None and error_x != 0:
        steps = min(max(abs(error_x) // 10, 1), 50)
        if error_x > 0:
            motor.step_axis("horizontal", True, steps=steps)
        else:
            motor.step_axis("horizontal", False, steps=steps)
        moved = True

    # Vertical (tilt) with smooth scaling
    if error_y is not None and error_y != 0:
        steps = min(max(abs(error_y) // 10, 1), 50)
        if error_y > 0:
            motor.step_axis("vertical", True, steps=steps)
        else:
            motor.step_axis("vertical", False, steps=steps)
        moved = True

    if not moved:
        motor.stop_all()

    print(f"[MOTOR] error_x={error_x}, error_y={error_y}")

def run():
    global running

    # -------------------------------
    # Start BLE server in background
    # -------------------------------
    def _start_ble():
        asyncio.run(ble_run())

    ble_thread = threading.Thread(target=_start_ble, daemon=True)
    ble_thread.start()
    print("[BLE] Server started in background thread")

    print("Initializing systems...")
    init_user_detection()
    print("Initializing IMU...")
    tracker = OrientationTracker(interrupt_pin=17)
    tracker.start()
    print("IMU tracking active.")

    try:
        while running:
            loop_start = time.time()

            # -------------------------------
            # 1. Sun Sensor Data
            # -------------------------------
            alpha, beta, sun_error = get_sun_sensor_data()

            # -------------------------------
            # 2. User Detection
            # -------------------------------
            error_x, error_y = get_user_errors()

            # -------------------------------
            # 2.5 IMU Orientation
            # -------------------------------
            roll, pitch, yaw = tracker.get_orientation()

            # -------------------------------
            # 3. Mode Logic
            # -------------------------------
            with state_lock:
                mode = state.mode

            # Decide what errors to feed the motor controller
            if mode == "Manual":
                direction = state.manual_direction

                if direction == "left":
                    error_x_cmd = -5
                    error_y_cmd = 0
                elif direction == "right":
                    error_x_cmd = 5
                    error_y_cmd = 0
                elif direction == "up":
                    error_x_cmd = 0
                    error_y_cmd = 5
                elif direction == "down":
                    error_x_cmd = 0
                    error_y_cmd = -5
                else:
                    error_x_cmd = 0
                    error_y_cmd = 0

            elif mode == "Auto":
                # -------------------------------
                # Blended User + Sun Control
                # -------------------------------

                # Compute sun-relative error using IMU
                sun_yaw_error = alpha - yaw
                sun_pitch_error = beta - pitch

                # Normalize yaw error to [-180, 180]
                sun_yaw_error = (sun_yaw_error + 180) % 360 - 180

                # Weights
                W_USER = 0.7
                W_SUN  = 0.3

                if error_x is None:
                    print("[AUTO] No user detected → tracking sun")
                    error_x_cmd = sun_yaw_error
                    error_y_cmd = sun_pitch_error
                else:
                    # Blend user centering with sun alignment
                    error_x_cmd = W_USER * error_x + W_SUN * sun_yaw_error
                    error_y_cmd = W_USER * error_y + W_SUN * sun_pitch_error

                    # Hard constraint: keep user in frame
                    if abs(error_x) > 100:
                        error_x_cmd = error_x
                    if abs(error_y) > 100:
                        error_y_cmd = error_y

            else:
                error_x_cmd, error_y_cmd = 0.0, 0.0

            # -------------------------------
            # 4. Motor Output
            # -------------------------------
            send_motor_commands(error_x_cmd, error_y_cmd)

            # -------------------------------
            # 5. Debug Logging
            # -------------------------------
            print(f"[SUN] alpha={alpha:.2f}, beta={beta:.2f}, err={sun_error}")
            sun_alignment_error = (sun_yaw_error**2 + sun_pitch_error**2) ** 0.5
            print(f"[SUN ALIGN] yaw_err={sun_yaw_error:.2f}°, pitch_err={sun_pitch_error:.2f}°, total_err={sun_alignment_error:.2f}°")
            print(f"[USER] err_x={error_x}, err_y={error_y}")
            print(f"[MODE] {mode}")
            print(f"[IMU] roll={roll:.2f}, pitch={pitch:.2f}, yaw={yaw:.2f}")
            print("-" * 40)

            # -------------------------------
            # 6. Loop Timing
            # -------------------------------
            elapsed = time.time() - loop_start
            sleep_time = max(0, (1.0 / LOOP_HZ) - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("Shutting down...")

    finally:
        shutdown_user_detection()
        try:
            tracker.stop()
        except Exception:
            pass


# Entry Point
if __name__ == "__main__":
    run()