import cv2
import time
import numpy as np
import ai_edge_litert.interpreter as tflite
import os
from picamera2 import Picamera2

MOTOR_HZ = 10
FRAME_W = 640
FRAME_H = 480
DEAD_ZONE = 40
ALPHA = 0.7

class MoveNetPoseDetector:
    def __init__(self, model_path):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"MoveNet model not found at {model_path}.")

        self.interpreter = tflite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details  = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.input_height = self.input_details[0]['shape'][1]
        self.input_width  = self.input_details[0]['shape'][2]

    def detect(self, frame):
        img = cv2.resize(frame, (self.input_width, self.input_height))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        input_tensor = np.expand_dims(img, axis=0).astype(np.uint8)
        self.interpreter.set_tensor(self.input_details[0]['index'], input_tensor)
        self.interpreter.invoke()
        keypoints = self.interpreter.get_tensor(self.output_details[0]['index'])
        return keypoints[0][0]


def get_torso_center(keypoints):
    pts = []
    for i in [5, 6, 11, 12]:  # L/R shoulder, L/R hip
        y, x, conf = keypoints[i]
        if conf > 0.3:
            pts.append((x * FRAME_W, y * FRAME_H))
    if not pts:
        return None
    pts = np.array(pts)
    return int(np.mean(pts[:, 0])), int(np.mean(pts[:, 1]))


# --- Setup (runs once) ---
HEADLESS = os.environ.get("DISPLAY") is None

detector = MoveNetPoseDetector(model_path="movenet_lightning.tflite")

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"format": "BGR888", "size": (FRAME_W, FRAME_H)}
))
picam2.start()
time.sleep(0.5)
print("Camera started successfully")

prev_center = None
last_motor_update = time.time()
prev_time = time.time()

try:
    while True:
        frame = picam2.capture_array()
        keypoints = detector.detect(frame)

        center = get_torso_center(keypoints)
        if center is None:
            print("No user detected")
            continue

        # Smooth position
        if prev_center is None:
            cx, cy = center
        else:
            cx = int(ALPHA * prev_center[0] + (1 - ALPHA) * center[0])
            cy = int(ALPHA * prev_center[1] + (1 - ALPHA) * center[1])
        prev_center = (cx, cy)

        # Compute error
        error_x = cx - FRAME_W // 2
        error_y = cy - FRAME_H // 2

        # Dead zone
        if abs(error_x) < DEAD_ZONE:
            error_x = 0
        if abs(error_y) < DEAD_ZONE:
            error_y = 0

        # Rate-limited motor update
        now = time.time()
        if now - last_motor_update >= 1.0 / MOTOR_HZ:
            fps = 1 / (now - prev_time)
            print(f"error_x: {error_x:+4d}  error_y: {error_y:+4d}  FPS: {fps:.1f}")
            # TODO: send error_x, error_y to motor controller here
            last_motor_update = now

        prev_time = now

        if not HEADLESS:
            cv2.imshow("ShadeAI User Tracking", frame)
            if cv2.waitKey(1) == 27:
                break

finally:
    picam2.stop()
    if not HEADLESS:
        cv2.destroyAllWindows()