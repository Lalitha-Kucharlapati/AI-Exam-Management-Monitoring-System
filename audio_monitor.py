import speech_recognition as sr
import tkinter as tk
import threading
import time
from shared_flags import status_flags, violation_count, monitoring_flags

voice_warnings = {}

def show_popup(msg):
    root = tk.Tk()
    root.withdraw()
    popup = tk.Toplevel()
    popup.title("Warning")
    popup.geometry("300x100")
    label = tk.Label(popup, text=msg, font=("Arial", 12))
    label.pack(pady=20)
    popup.after(3000, popup.destroy)
    root.mainloop()

def start_audio_monitoring(name):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print(f"🎤 Audio monitoring started for {name}...")
    monitoring_flags[name] = True
    violation_count[name] = violation_count.get(name, 0)

    while monitoring_flags.get(name, False):
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source)
                print("🔍 Listening for voice...")
                audio = recognizer.listen(source, timeout=5)

            text = recognizer.recognize_google(audio)
            print(f"🗣️ Detected voice: {text}")

            # ✅ Voice violation
            violation_count[name] += 1
            status_flags[name] = "Voice Warning"

            # ✅ Optional popup (safe in thread)
            threading.Thread(
                target=show_popup,
                args=(f"Voice detected! Warning {violation_count[name]}/3",),
                daemon=True
            ).start()

            if violation_count[name] >= 3:
                print("❌ Exam terminated due to voice detection.")
                status_flags[name] = "Terminated"
                monitoring_flags[name] = False
                break

        except sr.UnknownValueError:
            print("❗ Unclear sound detected — ignored.")
        except sr.WaitTimeoutError:
            print("⏱️ No sound detected within timeout window.")
        except Exception as e:
            print("Audio error:", e)

        time.sleep(2)
    
    print(f"🛑 Audio monitoring stopped for {name}")
