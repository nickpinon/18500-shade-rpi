"""
Mahony AHRS (Attitude and Heading Reference System) implementation
Algorithm based on original paper by Robert Mahony
Implementation based on jremington/LSM9DS1-AHRS
Coordinate system: North-West-Up (NWU)
"""

import math
import time

class MahonyFilter:
    def __init__(self, kp=2.0, ki=0.05, use_new_boards=False):
        # Kp (Proportional Gain): Controls convergence speed to accel/mag references.
        #   Higher = faster convergence but more noise sensitivity.
        #   Raised from 0.5 -> 2.0 to fix slow/inaccurate startup orientation.
        # Ki (Integral Gain): Corrects for long-term gyroscope bias/drift.
        #   Raised slightly to help with residual gyro bias after calibration.
        self.kp = kp
        self.ki = ki
        self.use_new_boards = use_new_boards
        self.q = [1.0, 0.0, 0.0, 0.0]  # Initial Quaternion (No rotation)
        self.e_int = [0.0, 0.0, 0.0]    # Integral error storage
        self.last_time = time.time()

    def update(self, g, a, m):
        """
        Updates the orientation quaternion based on 9DOF sensor data.
        g: gyro [rad/s], a: accel [g], m: mag [Gauss]
        """
        if self.use_new_boards:
            # Mapping for LSM6DSOX + LSM303AGR
            ax, ay, az = a[0], a[1], a[2]
            gx, gy, gz = g[0], g[1], g[2]
            mx, my, mz = m[1], m[0], -m[2]
        else:
            # Original LSM9DS1 mapping (Remington NWU convention)
            ax, ay, az = -a[0], -a[1], a[2]
            gx, gy, gz = -g[0], -g[1], g[2]
            mx, my, mz = -m[1], -m[0], -m[2]

        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        # Guard against very large dt on first call or pauses
        if dt > 0.1:
            dt = 0.1

        # Extract quaternion components for readability
        q1, q2, q3, q4 = self.q[0], self.q[1], self.q[2], self.q[3]

        # 1. Normalize Accelerometer — skip update if sensor is in freefall
        norm = math.sqrt(ax*ax + ay*ay + az*az)
        if norm < 1e-6:
            return self.get_euler()
        ax /= norm; ay /= norm; az /= norm

        # 2. Normalize Magnetometer — skip update if field is too weak
        norm = math.sqrt(mx*mx + my*my + mz*mz)
        if norm < 1e-6:
            return self.get_euler()
        mx /= norm; my /= norm; mz /= norm

        # 3. Reference direction of Earth's magnetic field (tilt-compensated)
        hx = 2.0 * (mx * (0.5 - q3*q3 - q4*q4) + my * (q2*q3 - q1*q4) + mz * (q2*q4 + q1*q3))
        hy = 2.0 * (mx * (q2*q3 + q1*q4) + my * (0.5 - q2*q2 - q4*q4) + mz * (q3*q4 - q1*q2))
        bx = math.sqrt(hx*hx + hy*hy)
        bz = 2.0 * (mx * (q2*q4 - q1*q3) + my * (q3*q4 + q1*q2) + mz * (0.5 - q2*q2 - q3*q3))

        # 4. Estimated direction of gravity and magnetic field
        vx = 2.0 * (q2*q4 - q1*q3)
        vy = 2.0 * (q1*q2 + q3*q4)
        vz = q1*q1 - q2*q2 - q3*q3 + q4*q4
        wx = 2.0 * (bx * (0.5 - q3*q3 - q4*q4) + bz * (q2*q4 - q1*q3))
        wy = 2.0 * (bx * (q2*q3 - q1*q4) + bz * (q1*q2 + q3*q4))
        wz = 2.0 * (bx * (q1*q3 + q2*q4) + bz * (0.5 - q2*q2 - q3*q3))

        # 5. Error is cross product between estimated and measured directions
        ex = (ay*vz - az*vy) + (my*wz - mz*wy)
        ey = (az*vx - ax*vz) + (mz*wx - mx*wz)
        ez = (ax*vy - ay*vx) + (mx*wy - my*wx)

        # 6. Apply integral feedback
        if self.ki > 0:
            self.e_int[0] += ex * dt
            self.e_int[1] += ey * dt
            self.e_int[2] += ez * dt
            gx += self.ki * self.e_int[0]
            gy += self.ki * self.e_int[1]
            gz += self.ki * self.e_int[2]

        # 7. Apply proportional feedback
        gx += self.kp * ex
        gy += self.kp * ey
        gz += self.kp * ez

        # 8. Integrate quaternion rate
        # FIX: All four original quaternion values must be used on the RIGHT-HAND
        # side. In the original code, q1 was overwritten first, then the new
        # (wrong) q1 was used when computing q2, q3, q4. Save all four first.
        q1_old, q2_old, q3_old, q4_old = q1, q2, q3, q4
        half_dt = 0.5 * dt
        q1 = q1_old + (-q2_old*gx - q3_old*gy - q4_old*gz) * half_dt
        q2 = q2_old + ( q1_old*gx + q3_old*gz - q4_old*gy) * half_dt
        q3 = q3_old + ( q1_old*gy - q2_old*gz + q4_old*gx) * half_dt
        q4 = q4_old + ( q1_old*gz + q2_old*gy - q3_old*gx) * half_dt

        # 9. Re-normalize quaternion
        norm = math.sqrt(q1*q1 + q2*q2 + q3*q3 + q4*q4)
        self.q = [q1/norm, q2/norm, q3/norm, q4/norm]

        return self.get_euler()

    def get_euler(self):
        """Converts quaternion to Roll, Pitch, Yaw (degrees)."""
        q = self.q
        roll  = math.atan2(2*(q[0]*q[1] + q[2]*q[3]), 1 - 2*(q[1]**2 + q[2]**2))
        pitch = math.asin(max(-1.0, min(1.0, 2*(q[0]*q[2] - q[3]*q[1]))))
        yaw   = math.atan2(2*(q[0]*q[3] + q[1]*q[2]), 1 - 2*(q[2]**2 + q[3]**2))
        return [math.degrees(roll), math.degrees(pitch), math.degrees(yaw)]