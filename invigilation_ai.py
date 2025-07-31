import cv2
import face_recognition
import numpy as np
import time
import base64
from shared_flags import status_flags, monitoring_flags, violation_count

# Capture a single face image before the exam
def capture_reference_face(name):
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    face_img = None
    print("📸 Please look at the camera. Capturing reference face...")

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("⚠️ Unable to read from camera.")
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = face_recognition.face_locations(rgb)

        if len(faces) == 1:
            top, right, bottom, left = faces[0]
            face_img = rgb[top:bottom, left:right]
            print("✅ Reference face captured.")
            break
        elif len(faces) > 1:
            print("⚠️ Multiple faces detected. Make sure only one face is visible.")
        else:
            print("⚠️ No face detected. Look at the camera.")

        cv2.imshow("Look at the camera - press ESC to skip", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("⏭️ Skipping reference face capture.")
            break

    cap.release()
    cv2.destroyAllWindows()

    if face_img is not None:
        _, buffer = cv2.imencode('.jpg', cv2.cvtColor(face_img, cv2.COLOR_RGB2BGR))
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        return img_base64
    else:
        return None


# Start monitoring the student during the exam
def start_camera_monitoring(name, reference_face_b64):
    print("🔄 Decoding reference face image...")
    try:
        ref_img_data = base64.b64decode(reference_face_b64)
        nparr = np.frombuffer(ref_img_data, np.uint8)
        ref_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if ref_img is None:
            print("❌ Reference image decoding failed.")
            return

        ref_rgb = cv2.cvtColor(ref_img, cv2.COLOR_BGR2RGB)
        ref_face_locations = face_recognition.face_locations(ref_rgb)
        if not ref_face_locations:
            print("❌ No face found in reference image.")
            return

        ref_encoding = face_recognition.face_encodings(ref_rgb, ref_face_locations)[0]
    except Exception as e:
        print(f"❌ Error decoding reference image: {e}")
        return

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    print(f"🧠 Monitoring started for {name}")
    monitoring_flags[name] = True
    violation_count[name] = 0

    while monitoring_flags.get(name, False):
        ret, frame = cap.read()
        if not ret or frame is None:
            print("⚠️ Failed to capture frame from camera.")
            time.sleep(1)
            continue
        for _ in range(5):
            if not monitoring_flags.get(name, False):
                break
            time.sleep(1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb)

        if len(face_locations) != 1:
            print("⚠️ Face issue: none or multiple faces detected.")
            status_flags[name] = "Face Warning"
            violation_count[name] += 1
        else:
            encodings = face_recognition.face_encodings(rgb, face_locations)
            if not encodings:
                print("⚠️ Could not extract face encoding.")
                status_flags[name] = "Face Warning"
                violation_count[name] += 1
                continue

            encoding = encodings[0]
            match = face_recognition.compare_faces([ref_encoding], encoding)[0]

            if not match:
                print("🚨 Face mismatch detected.")
                status_flags[name] = "Face Warning"
                violation_count[name] += 1
            else:
                print("✅ Face match confirmed.")
                status_flags[name] = "OK"

        if violation_count[name] >= 3:
            print(f"❌ {name} terminated due to repeated violations.")
            status_flags[name] = "Terminated"
            
            break

        time.sleep(5)

    cap.release()
    cv2.destroyAllWindows()
    print(f"🛑 Monitoring stopped for {name}")
