import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageEnhance
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

# Configuration
SERVER_IP = "10.145.9.167"
PHOTO_URL = f"http://{SERVER_IP}:8000/take_photo"
PING_URL = f"http://{SERVER_IP}:8000/ping"
SAVE_DIR = Path.home() / "Downloads" / "SnapdragonPhotos"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
ARDUINO_IP = "10.159.66.251"

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

def send_command_to_arduino(command):
    url = f"http://{ARDUINO_IP}/{command}"
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending command: {e}")
        return False

def get_arduino_status():
    url = f"http://{ARDUINO_IP}/"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            led_status = soup.find(text=lambda t: "LED Status:" in t)
            led_status_text = led_status.parent.get_text(strip=True) if led_status else "Unknown"
            return led_status_text
        else:
            return "Error fetching status"
    except Exception as e:
        print(f"Error fetching status: {e}")
        return "Error fetching status"

class SnapdragonCameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Snapdragon Wireless Camera + Arduino Control")
        self.root.geometry("750x520")
        self.root.configure(bg="white")

        self.auto_capturing = False

        self._build_gui()

        check_connection(self.snapdragon_conn_icon, PING_URL)
        self.update_arduino_status()

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

        # Arduino connection status
        header_arduino = tk.Frame(right_frame, bg="white")
        header_arduino.pack(fill="x", pady=(0, 20))
        tk.Label(header_arduino, text="Arduino Connection:", font=("Arial", 12), bg="white").pack(side="left")
        self.arduino_conn_icon = tk.Label(header_arduino, text="loading", font=("Arial", 14), bg="white")
        self.arduino_conn_icon.pack(side="left", padx=5)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(right_frame, textvariable=self.status_var, font=("Arial", 11), fg="blue", bg="white").pack(pady=(0, 15))

        # Camera controls
        tk.Label(right_frame, text="Camera Controls", font=("Arial", 14, "bold"), bg="white").pack()
        self.take_btn = tk.Button(right_frame, text="Take Photo", font=("Arial", 13), command=self.take_photo, width=22)
        self.take_btn.pack(pady=7)
        self.auto_btn = tk.Button(right_frame, text="Start Auto Capture", font=("Arial", 12), command=self.toggle_auto_capture, width=22)
        self.auto_btn.pack(pady=7)

        # Arduino controls
        tk.Label(right_frame, text="Arduino LED Control", font=("Arial", 14, "bold"), bg="white").pack(pady=(25, 5))
        btn_on = tk.Button(right_frame, text="Turn LED ON", font=("Arial", 12), command=lambda: self.arduino_command('H'), width=22)
        btn_on.pack(pady=5)
        btn_off = tk.Button(right_frame, text="Turn LED OFF", font=("Arial", 12), command=lambda: self.arduino_command('L'), width=22)
        btn_off.pack(pady=5)

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

    def arduino_command(self, cmd):
        success = send_command_to_arduino(cmd)
        if success:
            self.status_var.set(f"Sent Arduino command: {cmd}")
        else:
            self.status_var.set("Failed to send Arduino command")

    def update_arduino_status(self):
        def task():
            led_status = get_arduino_status()
            if "ON" in led_status or "OFF" in led_status:
                self.arduino_conn_icon.config(text="Good")
            else:
                self.arduino_conn_icon.config(text="Bad")
            self.root.after(5000, self.update_arduino_status)
        threading.Thread(target=task).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = SnapdragonCameraApp(root)
    root.mainloop()






