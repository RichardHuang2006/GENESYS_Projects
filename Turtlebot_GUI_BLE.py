import threading
import asyncio
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageEnhance
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from bleak import BleakClient
import numpy as np
from signalpow import get_vector
import time
from Move import move, move_next_row, correct_yaw, get_yaw_once
import math

# Configuration
SERVER_IP = "10.159.64.80"
PHOTO_URL = f"http://{SERVER_IP}:8000/take_photo"
PING_URL = f"http://{SERVER_IP}:8000/ping"
SAVE_DIR = Path.home() / "QualcommDataset/v6"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
ARDUINO_ADDR = "48:27:E2:E1:51:DD"
CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # write to BLE characteristic UUID
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
running = False

def save_and_process_image(raw_bytes, timestamp):
    filepath = SAVE_DIR / f"{timestamp}.jpg"
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

async def send_ble_command(command):
    try:
        async with BleakClient(ARDUINO_ADDR) as client:
            await client.write_gatt_char(CHAR_UUID, command.encode())
            return True
    except Exception as e:
        print(f"[BLE Error] {e}")
        return False

async def check_ble_connection():
    try:
        async with BleakClient(ARDUINO_ADDR) as client:
            if await client.is_connected():
                return True
    except Exception as e:
        print(f"[BLE] Not connected: {e}")
    return False

def get_arduino_status():
    import asyncio
    is_connected = asyncio.run(check_ble_connection())
    return "Connected" if is_connected else "Disconnected"

class SnapdragonCameraApp:
    running = False
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
        # Arduino BLE Command Entry
        tk.Label(right_frame, text="Send Arduino Command", font=("Arial", 14, "bold"), bg="white").pack(pady=(25, 5))

        self.ble_command_var = tk.StringVar()
        command_entry = tk.Entry(right_frame, textvariable=self.ble_command_var, font=("Arial", 12), width=22)
        command_entry.pack(pady=5)

        send_btn = tk.Button(right_frame, text="Send Command", font=("Arial", 12),
                            command=self.send_ble_command_from_input, width=22)
        send_btn.pack(pady=5)

        run_all_btn = tk.Button(right_frame, text="Capture Data", font=("Arial", 12),
                            command=self.full_system_run, width=22)
        run_all_btn.pack(pady=5)

    def take_photo(self):
        def task():
            self.status_var.set("Taking photo...")
            try:
                res = requests.get(PHOTO_URL, timeout=30)
                if res.status_code == 200:
                    filepath, tk_img = save_and_process_image(res.content, timestamp)
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

    def take_photo_now(self, timestamp):
        self.status_var.set("Taking photo...")
        try:
            res = requests.get(PHOTO_URL, timeout=30)
            if res.status_code == 200:
                filepath, tk_img = save_and_process_image(res.content, timestamp)
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
        if not cmd:
            self.status_var.set("Command is empty.")
            return False
        success = asyncio.run(send_ble_command(cmd))
        if success:
            self.status_var.set(f"Sent: '{cmd}'")
            print(f"[INFO]: Sent: '{cmd}'")
            return True
        else:
            self.status_var.set("Failed to send BLE command.")
            print("Failed to send BLE command. - arduinocommand")
            return False

    def update_arduino_status(self):
        def task():
            led_status = get_arduino_status()
            if "Connected" in led_status:
                self.arduino_conn_icon.config(text="Good")
            elif "Disconnected" in led_status:
                self.arduino_conn_icon.config(text="Bad")
            self.root.after(5000, self.update_arduino_status)
        threading.Thread(target=task).start()
    
    def send_ble_command_from_input(self):
        command = self.ble_command_var.get().strip()
        if not command:
            self.status_var.set("Command is empty.")
            return
        success = asyncio.run(send_ble_command(command))
        if success:
            self.status_var.set(f"Sent: '{command}'")
        else:
            self.status_var.set("Failed to send BLE command.")

    def capture_data(self):
        #if running:
        #    print("[INFO] Trying to run while again while running. Only click once!")
           
        wait_time = 0.01   
        success = False
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        signal_strength = []
        self.take_photo_now(timestamp)
        time.sleep(wait_time)
        while(not success):
            success = self.arduino_command("0")
        time.sleep(wait_time)
        signal_strength.append(np.array(get_vector()).mean())

        success = False
        while(not success):
            success = self.arduino_command("1")
        time.sleep(wait_time)
        signal_strength.append(np.array(get_vector()).mean())

        # success = False
        # while(not success):
        #     success = self.arduino_command("2")
        # time.sleep(wait_time)
        # signal_strength.append(np.array(get_vector()).mean())
        
        success = False
        while(not success):
            success = self.arduino_command("3")
        time.sleep(wait_time)
        signal_strength.append(np.array(get_vector()).mean())

        success = False
        while(not success):
            success = self.arduino_command("4")
        time.sleep(wait_time)
        signal_strength.append(np.array(get_vector()).mean())

        self.status_var.set("Signal Strength List: " + str(signal_strength))
        np.save( "/home/dolly/QualcommDataset/v6/" + timestamp + '.npy', np.array(signal_strength))
        print(f"[INFO] Finished running: " + str(signal_strength))
        print(np.argmax(signal_strength))

    def full_system_run(self):
        #self.capture_data()
        start_yaw = get_yaw_once(True)
        vel = 0.125
        for num in range(8):
            print("[INFO] Starting row: ", num)
            for num2 in range(76): # 76
                print("[INFO] Starting sample number: ", num2)
                self.capture_data()
                move(vel)
                correct_yaw(start_yaw)
            move_next_row()
            vel = vel*-1
            time.sleep(0.1)
            #start_yaw = (start_yaw + math.pi) % (2*math.pi) - math.pi

if __name__ == "__main__":
    root = tk.Tk()
    app = SnapdragonCameraApp(root)
    root.mainloop()






