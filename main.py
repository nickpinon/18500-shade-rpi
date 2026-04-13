#!/usr/bin/env python3
import sys
import os
import time
import threading
import asyncio

# Append subdirectories to path so Python can find your modules
sys.path.append(os.path.abspath("sensor"))
sys.path.append(os.path.abspath("ble"))
sys.path.append(os.path.abspath("user_detection"))

# Import your custom modules
from lsm9ds1 import ThreadedIMU
from mahony_fusion import MahonyFilter
from ble_server import run as ble_run, state as ble_state, state_lock, gpio
from userDetection import MoveNetPoseDetector, get_torso_center, FRAME_W, FRAME_H, DEAD_ZONE, ALPHA
from picamera2 import Picamera2

# Global state to share IMU orientation with CV/Motor logic
current_orientation = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
orientation_lock = threading.Lock()

# Thread locks to prevent stepping the same motor from two different threads at once
motor_locks = {
    "vertical": threading.Lock(),
    "horizontal": threading.Lock()
}

def safe_step_axis(axis, forward, steps):
    """Thread-safe wrapper to prevent concurrent motor commands on the same axis."""
    if motor_locks[axis].acquire(blocking=False):
        try:
            gpio.step_axis(axis, forward, steps)
        finally:
            motor_locks[axis].release()

def imu_worker():
    """Runs the interrupt-driven IMU loop."""
    print("[IMU] Worker starting...")
    try:
        # Check that bus_id and interrupt_pin match your hardware wiring
        imu = ThreadedIMU(bus_id=1, interrupt_pin=17) 
        imu.load_calibration("sensor/calibration.json")
        fusion = MahonyFilter(kp=0.5, ki=0.0)
        
        while True:
            # This efficiently blocks and yields the CPU until the hardware interrupt fires
            roll, pitch, yaw = imu.get_latest_fusion(fusion)
            
            with orientation_lock:
                current_orientation["roll"] = roll
                current_orientation["pitch"] = pitch
                current_orientation["yaw"] = yaw
                
    except Exception as e:
        print(f"[IMU] Worker failed: {e}")

def cv_worker():
    """Runs the TFLite camera perception and decides on motor outputs."""
    print("[CV] Worker starting...")
    detector = MoveNetPoseDetector(model_path="user_detection/movenet_lightning.tflite")
    
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(
        main={"format": "BGR888", "size": (FRAME_W, FRAME_H)}
    ))
    picam2.start()
    time.sleep(0.5)

    prev_center = None
    MOTOR_HZ = 10
    last_motor_update = time.time()

    try:
        while True:
            frame = picam2.capture_array()
            keypoints = detector.detect(frame)
            center = get_torso_center(keypoints)
            
            if center is None:
                continue

            # Exponential Moving Average Smoothing
            cx = int(ALPHA * prev_center[0] + (1 - ALPHA) * center[0]) if prev_center else center[0]
            cy = int(ALPHA * prev_center[1] + (1 - ALPHA) * center[1]) if prev_center else center[1]
            prev_center = (cx, cy)

            error_x = cx - FRAME_W // 2
            error_y = cy - FRAME_H // 2

            if abs(error_x) < DEAD_ZONE: error_x = 0
            if abs(error_y) < DEAD_ZONE: error_y = 0

            now = time.time()
            if now - last_motor_update >= 1.0 / MOTOR_HZ:
                
                # Retrieve current AHRS orientation
                with orientation_lock:
                    roll = current_orientation["roll"]
                    pitch = current_orientation["pitch"]
                
                # --- Basic Position-Gyro Logic ---
                # Combine physical CV error with Gyro tilt state here.
                # For this basic version, we just step motors directly to reduce the CV error.
                
                step_count = 200 # Adjust steps per detection cycle as needed

                if error_x > 0:
                    threading.Thread(target=safe_step_axis, args=("horizontal", True, step_count), daemon=True).start()
                elif error_x < 0:
                    threading.Thread(target=safe_step_axis, args=("horizontal", False, step_count), daemon=True).start()
                    
                if error_y > 0: # User is lower in frame
                    threading.Thread(target=safe_step_axis, args=("vertical", False, step_count), daemon=True).start()
                elif error_y < 0: # User is higher in frame
                    threading.Thread(target=safe_step_axis, args=("vertical", True, step_count), daemon=True).start()

                last_motor_update = now
    finally:
        picam2.stop()

def main():
    print("=== Starting Shade RPi Controller ===")
    
    # 1. Start IMU AHRS Thread (Interrupt Driven)
    imu_thread = threading.Thread(target=imu_worker, daemon=True)
    imu_thread.start()

    # 2. Start Computer Vision Thread (Continuous Polling)
    cv_thread = threading.Thread(target=cv_worker, daemon=True)
    cv_thread.start()

    # 3. Start BLE Server on the Main Thread (Asyncio Event Loop)
    # This also initializes lgpio stepping globally
    asyncio.run(ble_run())

if __name__ == "__main__":
    main()