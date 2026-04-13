#!/usr/bin/env python3
import sys
import os
import time
import threading
import csv
import argparse

# Path setup for sensor modules
sys.path.append(os.path.abspath("sensor"))
from lsm9ds1 import ThreadedIMU
from mahony_fusion import MahonyFilter

# Global orientation state
current_orientation = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
orientation_lock = threading.Lock()

# Global Performance Stats
perf_stats = {"cpu_us": 0.0, "debug_enabled": False}
LOG_FILE = "performance_log.csv"

def imu_worker():
    """Background thread for interrupt-driven IMU processing."""
    try:
        imu = ThreadedIMU(bus_id=1, interrupt_pin=17)
        # Always pulls the most recent values from the JSON file
        imu.load_calibration("sensor/calibration.json") 
        fusion = MahonyFilter(kp=0.5, ki=0.0)
        
        # Initialize log file only if debug is active
        if perf_stats["debug_enabled"]:
            with open(LOG_FILE, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Proc_Time_us", "Roll", "Pitch", "Yaw"])

        sample_count = 0
        while True:
            # Time the processing if debugging
            start_time = time.perf_counter() if perf_stats["debug_enabled"] else 0

            # Block until hardware interrupt
            roll, pitch, yaw = imu.get_latest_fusion(fusion)

            if perf_stats["debug_enabled"]:
                proc_time_us = (time.perf_counter() - start_time) * 1_000_000
                perf_stats["cpu_us"] = proc_time_us
                
                # Append to file every 120 samples (~once per second at 119Hz)
                sample_count += 1
                if sample_count >= 120:
                    with open(LOG_FILE, mode='a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([time.time(), f"{proc_time_us:.2f}", roll, pitch, yaw])
                    sample_count = 0

            with orientation_lock:
                current_orientation.update({"roll": roll, "pitch": pitch, "yaw": yaw})
                
    except Exception as e:
        print(f"\n[IMU Error]: {e}")

def main():
    parser = argparse.ArgumentParser(description="ShadeAI Top-Level Controller")
    parser.add_argument("--debug", action="store_true", help="Enable performance logging and terminal metrics")
    args = parser.parse_args()
    
    perf_stats["debug_enabled"] = args.debug
    
    print(f"=== ShadeAI Controller {'(DEBUG MODE)' if args.debug else ''} ===")
    
    imu_thread = threading.Thread(target=imu_worker, daemon=True)
    imu_thread.start()

    try:
        while True:
            with orientation_lock:
                r, p, y = current_orientation["roll"], current_orientation["pitch"], current_orientation["yaw"]
            
            output = f"R: {r:>6.1f}° P: {p:>6.1f}° Y: {y:>6.1f}°"
            
            if args.debug:
                output += f" | CPU: {perf_stats['cpu_us']:>6.2f}µs"
            
            print(output, end="\r", flush=True)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()