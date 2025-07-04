import cv2
import face_recognition
import numpy as np
import time
import base64
import os
from shared_flags import status_flags, monitoring_flags, violation_count


# Save one face image before the exam
def capture_reference_face(name):
    cap = cv2.VideoCapture(0)
    face_img = None
    print("Please look at the camera. Capturing reference face...")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = face_recognition.face_locations(rgb)

        if len(faces) == 1:
            top, right, bottom, left = faces[0]
            face_img = rgb[top:bottom, left:right]
            break

        cv2.imshow("Look at the camera - press ESC to skip", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

    if face_img is not None:
        # Save image as base64 (NO local npy save)
        _, buffer = cv2.imencode('.jpg', cv2.cvtColor(face_img, cv2.COLOR_RGB2BGR))
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        return img_base64
    return None


# Run live monitoring and compare faces
def start_camera_monitoring(name, reference_face_b64):
    ref_img_data = base64.b64decode(reference_face_b64)
    nparr = np.frombuffer(ref_img_data, np.uint8)
    ref_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    ref_rgb = cv2.cvtColor(ref_img, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(ref_rgb)
    if not face_locations:
        print("No face detected in reference image.")
        return

    ref_encoding = face_recognition.face_encodings(ref_rgb, face_locations)[0]

    cap = cv2.VideoCapture(0)
    print(f"🧠 Face monitoring started for {name}")
    monitoring_flags[name] = True
    violation_count[name] = 0  # Initialize violation count

    while monitoring_flags.get(name, False):
        ret, frame = cap.read()
        if not ret:
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb)

        if len(face_locations) != 1:
            print("⚠️ Face error: none or multiple faces.")
            status_flags[name] = "Face Warning"
            violation_count[name] += 1
        else:
            face_encoding = face_recognition.face_encodings(rgb, face_locations)[0]
            match = face_recognition.compare_faces([ref_encoding], face_encoding)[0]
            if not match:
                print("🚨 Face mismatch detected.")
                status_flags[name] = "Face Warning"
                violation_count[name] += 1
            else:
                # If everything is fine, clear warnings
                status_flags[name] = "OK"

        # Terminate if 3+ violations
        if violation_count[name] >= 3:
            print(f"❌ {name} terminated due to repeated face violations.")
            status_flags[name] = "Terminated"
            monitoring_flags[name] = False
            break

        time.sleep(5)

    cap.release()
    cv2.destroyAllWindows()
    print(f"🛑 Face monitoring stopped for {name}")