# 18500-shade-rpi

This repository contains the Raspberry Pi 5 software implementation for the **shade.ai** 18-500 Capstone Project. It serves as the central controller for the automated umbrella system, coordinating hardware peripherals, sensing, and user-tracking logic.

## Project Overview
The software implements a real-time control loop to maintain optimal shading by tracking user position and device orientation.

## Core Implementations
* **BLE Peripheral**: A GATT server for manual remote control, status monitoring, and receiving mobile location data.
* **IMU Sensing (LSM9DS1)**: High-frequency, interrupt-driven orientation tracking using Mahony AHRS fusion for precise pitch, roll, and yaw calculation.
* **Computer Vision Perception**: Real-time user detection and torso tracking using MoveNet Lightning and TFLite for targeted shading.
* **Stepper Motor Control**: Efficient, non-blocking horizontal and vertical axis positioning via GPIO-based pulse generation.
* **Main Coordination**: A multi-threaded architecture that synchronizes peripheral updates and performance logging.

## Hardware Configuration
For detailed wiring and pin mapping, refer to the [PINOUT.md](./PINOUT.md) file.