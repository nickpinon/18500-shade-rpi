"""
Integrator Script

Coordinates:
- Sun sensor emulator (alpha, beta, error_code)
- User detection (error_x, error_y)
- Manual control (app input → motor commands)

NOTE: GPIO motor control will be added later.
"""

from ..user_detection import init_user_detection, get_user_errors, shutdown_user_detection

# from ..sun_sensor import get_sun_sensor_data

import time
from ..ble.ble_server import state, state_lock
from .motor import motor


# Configuration
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
    # TODO: Replace with actual emulator call
    alpha = 0.0
    beta = 0.0
    error_code = 0
    return alpha, beta, error_code


# Manual Control Interface
def get_manual_input():
    """
    @brief Retrieve manual control input from app

    @return (left_cmd, right_cmd): motor commands
    """
    # TODO: Replace with app interface
    return 0, 0



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

    print("Initializing systems...")
    init_user_detection()

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
            # 3. Mode Logic
            # -------------------------------
            with state_lock:
                mode = state.mode
                manual_left = state.manual_left_cmd
                manual_right = state.manual_right_cmd

            if mode == "Manual":
                left_cmd = manual_left
                right_cmd = manual_right

            elif mode == "Auto":
                if error_x is None:
                    print("[AUTO] No user detected")
                    left_cmd, right_cmd = 0, 0
                else:
                    Kp = 0.01
                    left_cmd = -Kp * error_x
                    right_cmd = Kp * error_x

            else:
                left_cmd, right_cmd = 0, 0

            # -------------------------------
            # 4. Motor Output
            # -------------------------------
            send_motor_commands(error_x, error_y)

            # -------------------------------
            # 5. Debug Logging
            # -------------------------------
            print(f"[SUN] alpha={alpha:.2f}, beta={beta:.2f}, err={sun_error}")
            print(f"[USER] err_x={error_x}, err_y={error_y}")
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


# Entry Point
if __name__ == "__main__":
    run()