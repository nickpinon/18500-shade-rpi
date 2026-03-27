import cv2
import time
import numpy as np
import ai_edge_litert.interpreter as tflite
import os
from picamera2 import Picamera2


class MoveNetPoseDetector:
    def __init__(self, model_path):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"MoveNet model not found at {model_path}. "
                "Download the .tflite file manually.")

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
        return keypoints[0][0]  # (17, 3) -> (y, x, confidence)


FRAME_W = 640
FRAME_H = 480
prev_center = None
alpha = 0.7

# Initialize MoveNet detector
detector = MoveNetPoseDetector(model_path="movenet_lightning.tflite")

# Initialize picamera2
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"format": "BGR888", "size": (FRAME_W, FRAME_H)}
))
picam2.start()
time.sleep(0.5)  # warm-up
print("Camera started successfully")


def get_torso_center(keypoints):
    LEFT_SHOULDER  = 5
    RIGHT_SHOULDER = 6
    LEFT_HIP       = 11
    RIGHT_HIP      = 12

    pts = []
    for i in [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP]:
        y, x, conf = keypoints[i]
        if conf > 0.3:
            pts.append((x * FRAME_W, y * FRAME_H))

    if len(pts) == 0:
        return None

    pts = np.array(pts)
    return int(np.mean(pts[:, 0])), int(np.mean(pts[:, 1]))


try:
    while True:
        frame = picam2.capture_array()

        # Run MoveNet detection
        keypoints = detector.detect(frame)

        # Draw keypoints with confidence > 0.3
        for kp in keypoints:
            y, x, conf = kp
            if conf > 0.3:
                px = int(x * FRAME_W)
                py = int(y * FRAME_H)
                cv2.circle(frame, (px, py), 3, (255, 0, 0), -1)

        # Compute torso center
        center = get_torso_center(keypoints)

        if center is None:
            print("No user detected")
            continue

        # Smooth with exponential moving average
        if prev_center is None:
            cx, cy = center
        else:
            cx = int(alpha * prev_center[0] + (1 - alpha) * center[0])
            cy = int(alpha * prev_center[1] + (1 - alpha) * center[1])

        prev_center = (cx, cy)

        # Draw torso center
        cv2.circle(frame, (cx, cy), 8, (0, 255, 0), -1)

        # Compute error from image center
        error_x = cx - FRAME_W // 2
        error_y = cy - FRAME_H // 2

        # Apply dead zone
        dead_zone = 20
        if abs(error_x) < dead_zone:
            error_x = 0
        if abs(error_y) < dead_zone:
            error_y = 0

        print("error_x:", error_x, "error_y:", error_y)

        # Draw image center
        cv2.circle(frame, (FRAME_W // 2, FRAME_H // 2), 6, (0, 0, 255), -1)

        # Display frame
        HEADLESS = os.environ.get("DISPLAY") is None

        # Then at the bottom of the loop, replace the imshow block:
        if not HEADLESS:
            cv2.imshow("ShadeAI User Tracking", frame)
            if cv2.waitKey(1) == 27:
                break

        if cv2.waitKey(1) == 27:
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()