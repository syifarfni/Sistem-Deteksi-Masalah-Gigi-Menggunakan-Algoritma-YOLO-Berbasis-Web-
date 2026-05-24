from django.test import TestCase

# Create your tests here.
import cv2
import time
import os
import sys
from ultralytics import YOLO
import numpy as np

def load_model(weights_path='best.pt'):
    print(f"Loading model from {weights_path}...")
    model = YOLO(weights_path)
    print("Model loaded.")
    return model

def preprocess_frame(frame, max_size=640):
    h, w = frame.shape[:2]
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
    return frame

def postprocess_results(results, frame):
    # results[0] is the detection for this frame
    result_img = results[0].plot()  # Annotated BGR image
    num_detections = len(results[0].boxes)
    cv2.putText(result_img, f"Detections: {num_detections}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
    return result_img

def run_on_image(model, img_path):
    print(f"Running inference on image: {img_path}")
    img = cv2.imread(img_path)
    if img is None:
        print("Error: Could not read image.")
        return
    img = preprocess_frame(img)
    results = model(img)
    result_img = postprocess_results(results, img)
    cv2.imshow("Result", result_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def run_on_video(model, video_path):
    print(f"Running inference on video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Cannot open video.")
        return
    
    fps_start_time = time.time()
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("End of video or cannot fetch the frame.")
            break
        
        frame = preprocess_frame(frame)
        results = model(frame)
        result_img = postprocess_results(results, frame)
        
        frame_count += 1
        fps_end_time = time.time()
        fps = frame_count / (fps_end_time - fps_start_time)
        cv2.putText(result_img, f"FPS: {fps:.2f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)
        
        cv2.imshow("Video Result", result_img)
        key = cv2.waitKey(1)
        if key == 27:  # ESC to quit
            break
    cap.release()
    cv2.destroyAllWindows()

def run_on_camera(model, camera_id=0):
    print(f"Running inference on camera {camera_id}...")
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        print(f"Error: Cannot open camera {camera_id}.")
        return

    fps_start_time = time.time()
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame from camera.")
            break
        
        frame = preprocess_frame(frame)
        results = model(frame)
        result_img = postprocess_results(results, frame)
        
        frame_count += 1
        fps_end_time = time.time()
        fps = frame_count / (fps_end_time - fps_start_time)
        cv2.putText(result_img, f"FPS: {fps:.2f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)
        
        cv2.imshow("Camera Result", result_img)
        key = cv2.waitKey(1)
        if key == 27:  # ESC key to quit
            break
    cap.release()
    cv2.destroyAllWindows()

def main():
    if len(sys.argv) < 3:
        print("Usage: python test.py [mode] [input]")
        print("mode: image | video | camera")
        print("input: image_path | video_path | camera_id")
        return
    
    mode = sys.argv[1].lower()
    input_arg = sys.argv[2]
    
    model = load_model()  # default yolov8n.pt
    
    if mode == "image":
        run_on_image(model, input_arg)
    elif mode == "video":
        run_on_video(model, input_arg)
    elif mode == "camera":
        try:
            cam_id = int(input_arg)
        except:
            cam_id = 0
        run_on_camera(model, cam_id)
    else:
        print("Unknown mode. Use image, video, or camera.")

if __name__ == "__main__":
    main()
