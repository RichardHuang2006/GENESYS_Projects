import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageEnhance
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

# Configuration
SERVER_IP = "10.159.66.216"
PHOTO_URL = f"http://{SERVER_IP}:8000/take_photo"
PING_URL = f"http://{SERVER_IP}:8000/ping"
ARDUINO_ADDR = "48:27:E2:E1:51:DD"
CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # write to BLE characteristic UUID
SAVE_DIR = Path.home() / "Downloads" / "SnapdragonPhotos"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
def save_and_process_image(raw_bytes):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = SAVE_DIR / f"photo_{timestamp}.jpg"
    with open(filepath, "wb") as f:
        f.write(raw_bytes)
    img = Image.open(filepath).resize((400, 300), Image.Resampling.LANCZOS)
    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = ImageEnhance.Brightness(img).enhance(1.3)
    return filepath, ImageTk.PhotoImage(img)

def check_connection(label_widget, url):
    def task():
        try:
            res = requests.get(url, timeout=3)
            if res.status_code == 200 and "pong" in res.text.lower():
                label_widget.config(text="good", fg="green")
            else:
                label_widget.config(text="warning", fg="orange")
        except:
            label_widget.config(text="bad", fg="red")
    threading.Thread(target=task).start()

class SnapdragonCameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Snapdragon Wireless Camera")
        self.root.geometry("750x520")
        self.root.configure(bg="white")

        self.auto_capturing = False

        self._build_gui()

        check_connection(self.snapdragon_conn_icon, PING_URL)

    def _build_gui(self):
        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left frame (photo display)
        left_frame = tk.Frame(main_frame, bg="black", width=420, height=340)
        left_frame.pack(side="left", fill="both", expand=False)
        left_frame.pack_propagate(False)
        self.image_label = tk.Label(left_frame, bg="gray", width=400, height=300)
        self.image_label.pack(expand=True)

        # Right frame (controls)
        right_frame = tk.Frame(main_frame, bg="white", width=300)
        right_frame.pack(side="left", fill="y", expand=False, padx=(15, 0))
        right_frame.pack_propagate(False)

        # Snapdragon connection status
        header_snapdragon = tk.Frame(right_frame, bg="white")
        header_snapdragon.pack(fill="x", pady=(0, 10))
        tk.Label(header_snapdragon, text="Snapdragon Connection:", font=("Arial", 12), bg="white").pack(side="left")
        self.snapdragon_conn_icon = tk.Label(header_snapdragon, text="loading", font=("Arial", 14), bg="white")
        self.snapdragon_conn_icon.pack(side="left", padx=5)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(right_frame, textvariable=self.status_var, font=("Arial", 11), fg="blue", bg="white").pack(pady=(0, 15))

        # Camera controls
        tk.Label(right_frame, text="Camera Controls", font=("Arial", 14, "bold"), bg="white").pack()
        self.take_btn = tk.Button(right_frame, text="Take Photo", font=("Arial", 13), command=self.take_photo, width=22)
        self.take_btn.pack(pady=7)
        self.auto_btn = tk.Button(right_frame, text="Start Auto Capture", font=("Arial", 12), command=self.toggle_auto_capture, width=22)
        self.auto_btn.pack(pady=7)

    def take_photo(self):
        def task():
            self.status_var.set("Taking photo...")
            try:
                res = requests.get(PHOTO_URL, timeout=30)
                if res.status_code == 200:
                    filepath, tk_img = save_and_process_image(res.content)
                    self.image_label.config(image=tk_img)
                    self.image_label.image = tk_img
                    self.status_var.set(f"Saved: {filepath.name}")
                    print(f"[INFO] Saved image to: {filepath}")
                else:
                    self.status_var.set(f"Server error: {res.status_code}")
                    messagebox.showerror("Error", f"Server error: {res.status_code}")
            except Exception as e:
                self.status_var.set("Failed to connect")
                messagebox.showerror("Error", f"Failed to get photo:\n{e}")
        threading.Thread(target=task).start()

    def toggle_auto_capture(self):
        self.auto_capturing = not self.auto_capturing
        if self.auto_capturing:
            self.auto_btn.config(text="Stop Auto Capture")
            self.schedule_auto_capture()
        else:
            self.auto_btn.config(text="Start Auto Capture")
            self.status_var.set("Auto capture stopped.")

    def schedule_auto_capture(self):
        if self.auto_capturing:
            self.take_photo()
            self.root.after(10000, self.schedule_auto_capture)

if __name__ == "__main__":
    root = tk.Tk()
    app = SnapdragonCameraApp(root)
    root.mainloop()






