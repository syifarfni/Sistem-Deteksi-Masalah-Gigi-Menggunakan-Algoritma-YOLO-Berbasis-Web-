from django.shortcuts import render

# Create your views here
def home(request):
    return render(request, 'home.html')

from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseNotFound
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import RiwayatDeteksi
from django.core.files import File
from django.urls import path, re_path
from ultralytics import YOLO
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import os
import time
import threading
from collections import Counter
from .models import RiwayatDeteksi
from PIL import Image as PILImage

# -------------------------------- RIWAYAT DETEKSI --------------------------------------
@login_required
def riwayat(request):
    data= RiwayatDeteksi.objects.filter(user=request.user).order_by('-id')
    result = []
    optimize = request.GET.get('optimize', 'false').lower() == 'true'
    
    for item in data:
        foto_url = item.foto_hasil.url
        
        # Add a parameter to the URL to indicate thumbnail size for frontend optimization
        if optimize:
            foto_url = f"{foto_url}?size=thumbnail"
            
        result.append({
            'hasil_diagnosa': item.hasil_diagnosa,
            'foto_hasil': foto_url,
            'tanggal': item.tanggal.strftime('%d-%m-%Y')
        })
    return JsonResponse({'riwayat': result})


# Class name mapping untuk label YOLO
CLASS_NAMES = {
    0: "gingivitis",
    1: "karang gigi",
    2: "karies"
}

# Mendapatkan path absolut ke file model
model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "weights", "best.pt")

# Global variables
model = None
model_loading = False
is_model_loaded = False
is_live_detection_on = False


# Function to load model in background
def load_model_in_background():
    global model, model_loading, is_model_loaded
    
    if model_loading or is_model_loaded:
        return
        
    model_loading = True
    
    def _load_model():
        global model, model_loading, is_model_loaded
        
        try:
            # Load with optimized settings for inference
            model = YOLO(model_path)
            
            # Set input size to 640x640 for better accuracy
            model.overrides['imgsz'] = 640  # Changed from 416 to 640
            model.overrides['conf'] = 0.25  # Confidence threshold
            model.overrides['iou'] = 0.45   # NMS IOU threshold
            model.overrides['max_det'] = 10 # Max detections
            
            # Run one inference to initialize the model (instead of warmup)
            dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)  # Changed from 416 to 640
            _ = model(dummy_img, verbose=False)  # Silently initialize
            
            print("YOLO model loaded successfully")
            is_model_loaded = True
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
        finally:
            model_loading = False
    
    # Start loading model in background
    thread = threading.Thread(target=_load_model)
    thread.daemon = True
    thread.start()

# Load model on startup
load_model_in_background()

# Dictionary to store active camera streams
active_cameras = {}

# Function to get camera by id
def get_camera(camera_id=0):
    """Get a camera by ID, creates a new one if doesn't exist"""
    global active_cameras
    
    # Convert to int
    try:
        camera_id = int(camera_id)
    except (ValueError, TypeError):
        camera_id = 0
    
    # Check if camera already exists and is open
    if camera_id in active_cameras:
        cap = active_cameras[camera_id]
        if cap.isOpened():
            return cap
        else:
            # Close the inactive camera
            cap.release()
            del active_cameras[camera_id]
    
    # Create a new camera
    try:
        cap = cv2.VideoCapture(camera_id)
        
        # Cek apakah kamera berhasil dibuka
        if not cap.isOpened():
            print(f"Failed to open camera with ID: {camera_id}")
            # Fallback to default camera if specified camera can't be opened
            if camera_id != 0:
                cap = cv2.VideoCapture(0)
                camera_id = 0
        
        # Set resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Set buffer size to 1 to get the most recent frame
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Store the camera
        active_cameras[camera_id] = cap
        return cap
    except Exception as e:
        print(f"Error opening camera {camera_id}: {e}")
        return None

# Ensure CSRF cookie is set for the main page
@ensure_csrf_cookie
def home(request):
    # Ensure model is loading or loaded
    if not model_loading and not is_model_loaded:
        load_model_in_background()
    return render(request, 'home.html')

# Either use csrf_exempt or ensure_csrf_cookie based on your security needs
@ensure_csrf_cookie
def detect_objects(request):
    """Mendeteksi objek dari gambar yang diunggah."""
    global model, is_model_loaded
    
    # Load model if not already loaded
    if not is_model_loaded:
        if not model_loading:
            load_model_in_background()
        return JsonResponse({"error": "Model is still loading. Please try again in a few seconds."}, status=503)
    
    if request.method == "POST" and request.FILES.get("image"):
        try:
            start_time = time.time()
            image_file = request.FILES["image"]
            image = Image.open(image_file).convert("RGB")

            # buat logging
            # 🔍 LOG: Metadata Gambar Masuk
            print("\n🟢 --- LOG METADATA GAMBAR ---")
            print(f"Nama file        : {image_file.name}")
            print(f"Format PIL       : {image.format}")
            print(f"Mode warna       : {image.mode}")
            print(f"Ukuran (W x H)   : {image.width} x {image.height}")
            print("Resolution:", img.size)


            # Konversi ke NumPy dan log detail array
            img_np = np.array(image)
            print(f"Shape NumPy      : {img_np.shape}")
            print(f"Dtype NumPy      : {img_np.dtype}")
            print(f"Contoh pixel [0,0]: {img_np[0,0] if img_np.ndim == 3 else img_np[0]}")

            # Konversi gambar ke OpenCV format
            img_cv = np.array(image)
            
            # Buat folder untuk menyimpan hasil jika belum ada
            save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "detection_results")
            os.makedirs(save_dir, exist_ok=True)
            
            # Simpan gambar original untuk debugging (already in RGB from PIL)
            original_path = os.path.join(save_dir, f"original_{int(time.time())}.jpg")
            cv2.imwrite(original_path, cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR))  # Convert to BGR for OpenCV
            print(f"Original image saved to {original_path}")
            
            # Resize untuk performa lebih baik jika gambar terlalu besar
            h, w = img_cv.shape[:2]
            if max(h, w) > 640:
                scale = 640 / max(h, w)
                img_cv = cv2.resize(img_cv, (int(w * scale), int(h * scale)))
            
            # PENTING: PIL returns RGB, but YOLO expects BGR, so convert
            img_cv_bgr = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
            
            # Jalankan deteksi dengan confidence rendah untuk deteksi yang lebih sensitif
            results = model(img_cv_bgr, conf=0.1, verbose=True)  # Verbose=True untuk debugging
            print('deteksi', results)
            print(f"Detection took {time.time() - start_time:.3f} seconds")
            
            # Debug: Inspect the boxes to check if any detections are present
            if len(results) > 0:
                print(f"Number of detections: {len(results[0].boxes)}")
                if len(results[0].boxes) > 0:
                    print(f"Detection confidence: {results[0].boxes.conf}")
                    print(f"Detection classes: {results[0].boxes.cls}")
                else:
                    print("No boxes detected with current confidence threshold")

            # Plot deteksi
            result_image = results[0].plot()  # Returns BGR image
            print("Plot shape:", result_image.shape)
            
            # Simpan hasil deteksi ke file (in BGR format)
            result_path = os.path.join(save_dir, f"detection_{int(time.time())}.jpg")
            cv2.imwrite(result_path, result_image)  # OpenCV expects BGR
            print(f"Detection result saved to {result_path}")

            
            # Konversi hasil ke base64 agar bisa ditampilkan di frontend
            # No need to convert to RGB since the YOLO plot function already gives BGR which is what imencode expects
            _, buffer = cv2.imencode(".jpg", result_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
            image_base64 = base64.b64encode(buffer).decode("utf-8")


            detections = []
            for result in results:
                print('hasil', result)
                boxes = result.boxes
                print(f"Processing {len(boxes)} detection boxes")

                for i, box in enumerate(boxes):
                    try:
                        x1, y1, x2, y2, = map(int, box.xyxy[0])
                        conf = float(box.conf[0])
                        class_id = int(box.cls[0])

                        # model mengembalikan "0", "1", "2" sebagai names, tapi memastikan mapping yang sesuai
                        class_name = CLASS_NAMES.get(class_id, f"class_{class_id}")
                        print(f"Detection {i}: Class = {class_name},Confidence = {conf:.2f}, box={[x1, y1, x2, y2]}")

                        detections.append ({
                            "class": class_name,
                            "class_id":class_id,
                            "confidence": round (conf * 100, 2),
                            "box":[x1, y1, x2, y2]
                        })
                    except Exception as e:
                        print(f"Error processing dataections {i}:{e}")

            # menambahkan pesan berdasarkan hasil results
            response_message = "Tidak ada masalah gigi yang terdeteksi. Gigi tampak sehat."
            if detections:
                # Ambil class dan confidence
                conditions = [d["class"].lower() for d in detections]
                confidence_levels = [d["confidence"] for d in detections]

                # Hitung jumlah setiap jenis class
                counts = Counter(conditions)

                # Buat kalimat ringkasan
                summary_parts = []
                for cls, count in counts.items():
                    summary_parts.append(f"{count} {cls}")

                response_message = f"{', '.join(summary_parts)} terdeteksi. "
                response_message += f"Confidence tertinggi: {max(confidence_levels):.1f}%"


            # simpan ke database
            if request.user.is_authenticated:
                try:
                    # Open and optimize the image using PIL
                    with PILImage.open(result_path) as img:
                        # Resize if image is too large
                        max_size = 1200  # Maximum width or height
                        if max(img.width, img.height) > max_size:
                            # Maintain aspect ratio
                            ratio = max_size / max(img.width, img.height)
                            new_size = (int(img.width * ratio), int(img.height * ratio))
                            img = img.resize(new_size, PILImage.LANCZOS)
                        
                        # Save optimized image to memory buffer
                        buffer = BytesIO()
                        img.save(buffer, format='JPEG', quality=85, optimize=True)
                        buffer.seek(0)
                        
                        # Create Django file object from buffer
                        filename = os.path.basename(result_path)
                        django_file = File(buffer, name=filename)
                        
                        # Save to database
                        RiwayatDeteksi.objects.create(
                            user=request.user,
                            hasil_diagnosa=response_message,
                            foto_hasil=django_file
                        )
                except Exception as e:
                    print(f"Error optimizing image: {e}")
                    # Fallback to original method if optimization fails
                    with open(result_path, "rb") as f:
                        django_file = File(f)
                        filename = os.path.basename(result_path)
                        django_file.name = filename
                        RiwayatDeteksi.objects.create (
                            user=request.user,
                            hasil_diagnosa=response_message,
                            foto_hasil=django_file
                        )
            
            return JsonResponse({
                "image": image_base64,
                # "detections": num_detections,
                "detections": detections,
                #"message": detection_message,
                "messages": response_message,
                "processing_time": round((time.time() - start_time) * 1000),  # ms
                "saved_path": result_path
            })
        except Exception as e:
            print(f"Error in detect_objects: {e}")
            import traceback
            traceback.print_exc()  # Print full stack trace for debugging
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)

# Create a loading image
def create_loading_image():
    """Create a loading image with a message"""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, "Loading YOLO model...", (150, 240), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    return img

# Generator function to handle streaming from camera
def generate_frames(camera_id=0):
    """Generate video frames with object detection."""
    global model, is_model_loaded, is_live_detection_on
    
    # Variables for frame skipping and performance tracking
    frame_count = 0
    last_detection_time = 0
    detection_interval = 0.3  # Run detection every 0.3 seconds
    fps_start_time = time.time()
    fps_frame_count = 0
    fps = 0
    last_result_image = None
    skip_frames = 2  # Start with processing every 3rd frame (adaptive)
    
    # If model is not loaded, create a loading image
    if not is_model_loaded:
        if not model_loading:
            load_model_in_background()
        
        loading_img = create_loading_image()
        _, buffer = cv2.imencode('.jpg', loading_img)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n\r\n')

    # Get the camera
    cap = get_camera(camera_id)
    if cap is None:
        # Return error frame if camera can't be opened
        error_img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_img, f"Camera {camera_id} not available", (120, 240), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        _, buffer = cv2.imencode('.jpg', error_img)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n\r\n')
        return
    
    # Wait for model to be loaded
    while not is_model_loaded:
        # Create a waiting image
        loading_img = create_loading_image()
        _, buffer = cv2.imencode('.jpg', loading_img)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n\r\n')
        time.sleep(0.5)
    
    try:
        # while True:
        while is_live_detection_on:
            # Try to read frame
            for _ in range(skip_frames):
                success, frame = cap.read()
                if not success:
                    break
            
            if not success:
                print(f"Failed to read frame from camera {camera_id}")
                # Return a black frame with error message if we can't read a frame
                error_img = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(error_img, "Camera disconnected", (180, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                _, buffer = cv2.imencode('.jpg', error_img)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n\r\n')
                break
            
            # Calculate FPS
            fps_frame_count += 1
            elapsed_time = time.time() - fps_start_time
            if elapsed_time > 1.0:  # Update FPS every second
                fps = fps_frame_count / elapsed_time
                fps_frame_count = 0
                fps_start_time = time.time()
                
                # Adaptive frame skipping based on FPS
                if fps < 10 and skip_frames < 5:
                    skip_frames += 1
                elif fps > 25 and skip_frames > 0:
                    skip_frames -= 1
            
            # Increment frame count
            frame_count += 1
            
            # Only run detection on some frames to improve performance
            current_time = time.time()
            run_detection = current_time - last_detection_time > detection_interval
                
            # Use the cached result if detection is not needed
            if not run_detection and last_result_image is not None:
                result_image = last_result_image
            else:
                try:
                    # Resize frame if needed for faster processing
                    h, w = frame.shape[:2]
                    if max(h, w) > 640:
                        scale = 640 / max(h, w)
                        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
                    
                    # Note: frame is already in BGR format from cv2.VideoCapture, so no conversion needed
                    
                    # Run detection with standard confidence threshold
                    results = model(frame, conf=0.1, verbose=False)  # Lowered confidence for better detection
                    
                    # Use model's built-in plotting function (returns BGR image)
                    result_image = results[0].plot()
                    
                    # Save detection result every second
                    if current_time - last_detection_time >= 1.0:
                        # Create folder if it doesn't exist
                        save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "detection_results")
                        os.makedirs(save_dir, exist_ok=True)
                        
                        # Save the frame (already in BGR format for OpenCV)
                        result_path = os.path.join(save_dir, f"live_detection_{int(current_time)}.jpg")
                        cv2.imwrite(result_path, result_image)
                        print(f"Live detection result saved to {result_path}")
                    
                    # Draw camera ID and FPS info directly on the BGR image
                    cv2.putText(result_image, f"Camera: {camera_id}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(result_image, f"FPS: {fps:.1f}", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    # Add detection count
                    num_detections = len(results[0].boxes)
                    cv2.putText(result_image, f"Deteksi: {num_detections}", (10, 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    # Cache the result (BGR format)
                    last_result_image = result_image.copy()
                    last_detection_time = current_time
                except Exception as e:
                    print(f"Error in detection: {e}")
                    # Use the original frame if detection fails
                    result_image = frame
                    cv2.putText(result_image, f"Detection error: {str(e)[:30]}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # For frames without detection, still draw camera ID and FPS
            if not run_detection:
                cv2.putText(result_image, f"Camera: {camera_id}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(result_image, f"FPS: {fps:.1f}", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Convert to JPEG with slightly lower quality for better streaming performance
            # Use result_image_rgb if available (in detection case) or original frame for non-detection frames
            output_frame = result_image if not run_detection else result_image
            _, buffer = cv2.imencode('.jpg', output_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            # Yield the frame in the format expected by StreamingHttpResponse
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n\r\n')
            
    except Exception as e:
        print(f"Error in generate_frames: {e}")
    finally:
        # Don't close the camera here, we're keeping it open for reuse
        # pass
        if cap is not None:
            cap.release()
            print(f"Camera {camera_id} released.")



@csrf_exempt
def detect_camera(request, camera_id=0):
    """Display real-time detection results from the camera stream."""
    global is_live_detection_on

    if request.method == "POST":
        action = request.POST.get("action", "").lower()
        if action == "stop":
            is_live_detection_on = False
            print("Live detection manually stopped by client.")
            return JsonResponse({"status": "stopped"})
        else:
            return JsonResponse({"error": "Invalid POST action"}, status=400)

    elif request.method == "GET":
        is_live_detection_on = True
        try:
            return StreamingHttpResponse(
                generate_frames(camera_id),
                content_type="multipart/x-mixed-replace; boundary=frame"
            )
        except Exception as e:
            print(f"Error in detect_camera: {e}")
            return HttpResponseNotFound("Camera not available")
    
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)