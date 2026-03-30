"""
Mahnoy AHRS (Attitude and Heading Reference System) implementation
Algorithm based on original paper by Robert Mahony
Implmenentation based on jremington/LSM9DS1-AHRS
Coordinate system: North-West-Up (NWU)
"""

import math
import time

class MahonyFilter:
    def __init__(self, kp=0.5, ki=0.0):
        # Kp (Proportional Gain): Controls the rate of convergence to accel/mag references.
        # Ki (Integral Gain): Corrects for long-term gyroscope bias/drift.
        self.kp = kp
        self.ki = ki
        self.q = [1.0, 0.0, 0.0, 0.0]  # Initial Quaternion (No rotation)
        self.e_int = [0.0, 0.0, 0.0]    # Integral error storage
        self.last_time = time.time()

    def update(self, g, a, m):
        """
        Updates the orientation quaternion based on 9DOF sensor data.
        g: gyro [rad/s], a: accel [g], m: mag [Gauss]
        """
        # 1. Coordinate Remapping (LSM9DS1 -> NWU)
        # J. Remington identifies that the Mag axes are rotated relative to Accel/Gyro.
        ax, ay, az = -a[0], -a[1], a[2]
        gx, gy, gz = -g[0], -g[1], g[2]
        mx, my, mz = m[0], m[1], m[2]

        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        # Extract Quaternions for readability
        q = self.q
        q1, q2, q3, q4 = q[0], q[1], q[2], q[3]

        # 2. Normalize Accelerometer
        norm = math.sqrt(ax*ax + ay*ay + az*az)
        if norm == 0: return self.get_euler() # Handle singularity
        ax /= norm; ay /= norm; az /= norm

        # 3. Normalize Magnetometer
        norm = math.sqrt(mx*mx + my*my + mz*mz)
        if norm == 0: return self.get_euler()
        mx /= norm; my /= norm; mz /= norm

        # 4. Reference direction of Earth's magnetic field
        hx = 2.0 * (mx * (0.5 - q3*q3 - q4*q4) + my * (q2*q3 - q1*q4) + mz * (q2*q4 + q1*q3))
        hy = 2.0 * (mx * (q2*q3 + q1*q4) + my * (0.5 - q2*q2 - q4*q4) + mz * (q3*q4 - q1*q2))
        bx = math.sqrt(hx*hx + hy*hy)
        bz = 2.0 * (mx * (q2*q4 - q1*q3) + my * (q3*q4 + q1*q2) + mz * (0.5 - q2*q2 - q3*q3))

        # 5. Estimated direction of gravity and magnetic field
        vx = 2.0 * (q2*q4 - q1*q3)
        vy = 2.0 * (q1*q2 + q3*q4)
        vz = q1*q1 - q2*q2 - q3*q3 + q4*q4
        wx = 2.0 * (bx * (0.5 - q3*q3 - q4*q4) + bz * (q2*q4 - q1*q3))
        wy = 2.0 * (bx * (q2*q3 - q1*q4) + bz * (q1*q2 + q3*q4))
        wz = 2.0 * (bx * (q1*q3 + q2*q4) + bz * (0.5 - q2*q2 - q3*q3))

        # 6. Error is cross product between estimated and measured directions
        ex = (ay*vz - az*vy) + (my*wz - mz*wy)
        ey = (az*vx - ax*vz) + (mz*wx - mx*wz)
        ez = (ax*vy - ay*vx) + (mx*wy - my*wx)

        # 7. Apply feedback proportional and integral gains
        if self.ki > 0:
            self.e_int[0] += ex * dt
            self.e_int[1] += ey * dt
            self.e_int[2] += ez * dt
            gx += self.ki * self.e_int[0]
            gy += self.ki * self.e_int[1]
            gz += self.ki * self.e_int[2]
        
        gx += self.kp * ex
        gy += self.kp * ey
        gz += self.kp * ez

        # 8. Integrate Quaternion rate
        pa, pb, pc = q2, q3, q4
        q1 = q1 + (-q2*gx - q3*gy - q4*gz) * (0.5 * dt)
        q2 = pa + (q1*gx + pb*gz - pc*gy) * (0.5 * dt)
        q3 = pb + (q1*gy - pa*gz + pc*gx) * (0.5 * dt)
        q4 = pc + (q1*gz + pa*gy - pb*gx) * (0.5 * dt)

        # 9. Re-normalize Quaternion
        norm = math.sqrt(q1*q1 + q2*q2 + q3*q3 + q4*q4)
        self.q = [q1/norm, q2/norm, q3/norm, q4/norm]

        return self.get_euler()

    def get_euler(self):
        """Converts Quaternions to Roll, Pitch, Yaw (Degrees)."""
        q = self.q
        # Roll (x-axis rotation)
        roll = math.atan2(2*(q[0]*q[1] + q[2]*q[3]), 1 - 2*(q[1]**2 + q[2]**2))
        # Pitch (y-axis rotation)
        pitch = math.asin(max(-1.0, min(1.0, 2*(q[0]*q[2] - q[3]*q[1]))))
        # Yaw (z-axis rotation)
        yaw = math.atan2(2*(q[0]*q[3] + q[1]*q[2]), 1 - 2*(q[2]**2 + q[3]**2))
        
        return [math.degrees(roll), math.degrees(pitch), math.degrees(yaw)]