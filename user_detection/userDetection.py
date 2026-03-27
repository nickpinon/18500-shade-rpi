import cv2
import time
import numpy as np
import tflite_runtime.interpreter as tflite

# Load MoveNet model and allocate tensors
interpreter = tflite.Interpreter(model_path="movenet_singlepose_lightning.tflite")
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Open camera
cap = cv2.VideoCapture(0)

FRAME_W = 640
FRAME_H = 480
prev_center = None
alpha = 0.7

def get_torso_center(keypoints):
    # Calculate torso center from keypoints (shoulders and hips)
    LEFT_SHOULDER = 5
    RIGHT_SHOULDER = 6
    LEFT_HIP = 11
    RIGHT_HIP = 12

    pts = []

    for i in [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP]:
        y, x, conf = keypoints[i]
        if conf > 0.3:
            pts.append((x * FRAME_W, y * FRAME_H))

    if len(pts) == 0:
        return None

    pts = np.array(pts)
    center_x = np.mean(pts[:,0])
    center_y = np.mean(pts[:,1])

    return int(center_x), int(center_y)


while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (FRAME_W, FRAME_H))

    # Preprocess frame for MoveNet model
    img = cv2.resize(frame, (192,192))
    img = np.expand_dims(img, axis=0).astype(np.int32)

    interpreter.set_tensor(input_details[0]['index'], img)
    interpreter.invoke()

    # Get keypoints from model output
    keypoints = interpreter.get_tensor(output_details[0]['index'])
    keypoints = keypoints[0][0]

    # Draw keypoints with confidence > 0.3
    for kp in keypoints:
        y, x, conf = kp
        if conf > 0.3:
            px = int(x * FRAME_W)
            py = int(y * FRAME_H)
            cv2.circle(frame, (px, py), 3, (255,0,0), -1)

    # Compute torso center
    center = get_torso_center(keypoints)

    if center is None:
        print("No user detected")
        continue
    
    # Smooth center position with exponential moving average
    if prev_center is None:
        cx, cy = center
    else:
        cx = int(alpha * prev_center[0] + (1-alpha) * center[0])
        cy = int(alpha * prev_center[1] + (1-alpha) * center[1])

    prev_center = (cx, cy)

    # Draw detected torso center
    cv2.circle(frame, (cx, cy), 8, (0,255,0), -1)

    # Compute error from image center
    error_x = cx - FRAME_W//2
    error_y = cy - FRAME_H//2

    # Apply dead zone to ignore small movements
    dead_zone = 20
    if abs(error_x) < dead_zone:
        error_x = 0
    if abs(error_y) < dead_zone:
        error_y = 0

    print("error_x:", error_x, "error_y:", error_y)

    # Draw image center
    cv2.circle(frame, (FRAME_W//2, FRAME_H//2), 6, (0,0,255), -1)

    # Display the frame
    cv2.imshow("ShadeAI User Tracking", frame)

    if cv2.waitKey(1) == 27:
        break

    time.sleep(0.03)
    
cap.release()
cv2.destroyAllWindows()