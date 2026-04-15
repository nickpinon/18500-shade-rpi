# Shade.Ai Hardware Wiring Guide

This document defines the physical and logical pin mappings for the UmbrellaPi project. All software references use **BCM (GPIO) numbering**.

---

## 1. Peripheral Connection Table

| Peripheral | Function | BCM / GPIO | Physical Pin | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **LSM9DS1 IMU** | I2C SDA | **GPIO 2** | Pin 3 | Internal pull-up |
| | I2C SCL | **GPIO 3** | Pin 5 | Internal pull-up |
| | **Interrupt (DRDY)** | **GPIO 4** | **Pin 7** | **Changed from 17 to avoid conflict** |
| | VCC | 3.3V | Pin 1 | |
| | GND | Ground | Pin 9 | |
| **Vertical Motor** | Step | **GPIO 23** | Pin 16 | |
| | Direction | **GPIO 24** | Pin 18 | |
| | Enable | **GPIO 25** | Pin 22 | |
| **Horizontal Motor**| Step | **GPIO 17** | Pin 11 | |
| | Direction | **GPIO 27** | Pin 13 | |
| | Enable | **GPIO 22** | Pin 15 | |
| **Camera (CSI)** | Image Feed | N/A | MIPI Port | Ribbon cable connection |

---

## 2. Required Software Updates
Because of the pin conflict on GPIO 17 between the horizontal motor and the IMU interrupt, ensure your code reflects the following change:

### In `main.py` (or wherever `ThreadedIMU` is initialized):
```python
# Updated to use GPIO 4 for the hardware interrupt
imu = ThreadedIMU(bus_id=1, interrupt_pin=4)