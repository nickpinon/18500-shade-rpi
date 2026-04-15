#!/usr/bin/env python3
import time
import threading
from gpiozero import DigitalInputDevice
from lsm6dsox.lsm6dsox import LSM6DSOX
from lsm6dsox.lsm303agr import LSM303AGR
from mahony_fusion import MahonyFilter

class OrientationTracker:
    def __init__(self, bus_id=1, interrupt_pin=4, declination=-8.5, mount_offset=60.0):
        self.declination = declination
        self.mount_offset = mount_offset
        
        # Initialize Sensors
        self.imu = LSM6DSOX(bus_id=bus_id, bias_file="lsm6dsox/imu_bias.json")
        self.mag = LSM303AGR(bus_id=bus_id, bias_file="lsm6dsox/mag_bias.json")
        self.fusion = MahonyFilter(kp=5.0, ki=0.0, use_new_boards=True)
        
        # Thread-safe storage for Euler angles
        self._lock = threading.Lock()
        self._roll = 0.0
        self._pitch = 0.0
        self._yaw = 0.0
        
        # Concurrency primitives
        self._data_ready_event = threading.Event()
        self._running = False
        self._worker_thread = None

        # Setup GPIO Hardware Interrupt Listener
        # Uses gpiozero (standard for modern Pi OS) to detect the rising edge of INT1
        self.drdy_pin = DigitalInputDevice(interrupt_pin, pull_up=False)
        self.drdy_pin.when_activated = self._on_hardware_interrupt
        
        self._warmup_filter()

    def _warmup_filter(self):
        """Forces quick convergence on startup without blocking the main thread later."""
        self.fusion.kp = 10.0
        for _ in range(250):
            self.fusion.update(self.imu.read_gyro(), self.imu.read_accel(), self.mag.read_mag())
            time.sleep(0.002)
        self.fusion.kp = 5.0

    def _on_hardware_interrupt(self):
        """Minimal ISR: Signals the worker thread that data is ready."""
        self._data_ready_event.set()

    def _update_loop(self):
        """Background thread loop that blocks at 0% CPU until interrupted, with auto-recovery."""
        while self._running:
            # Wait for the interrupt. 
            # If 0.1s passes (meaning the pin might be stuck high), it stops waiting and moves on.
            self._data_ready_event.wait(timeout=0.1)
            self._data_ready_event.clear()
            
            try:
                # Fetch Data (This action forces the sensor to pull the interrupt pin back LOW)
                accel = self.imu.read_accel()
                gyro = self.imu.read_gyro()
                mag = self.mag.read_mag()

                # Process Fusion
                r, p, y = self.fusion.update(gyro, accel, mag)
                
                # Apply offsets
                true_yaw = (y + self.declination + self.mount_offset) % 360.0

                # Safely update state
                with self._lock:
                    self._roll = r
                    self._pitch = p
                    self._yaw = true_yaw
            except Exception as e:
                # If an I2C read collides or fails, it won't crash the invisible thread silently anymore
                print(f" Sensor Read Error: {e}")

    def start(self):
        """Spawns the background tracking thread."""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(target=self._update_loop, daemon=True)
            self._worker_thread.start()

    def stop(self):
        """Safely shuts down the tracking thread."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join()

    def get_orientation(self):
        """Fast, non-blocking method for the main Pi loop to get the latest data."""
        with self._lock:
            return self._roll, self._pitch, self._yaw