from flask import Flask, send_file
import os
import time

app = Flask(__name__)

@app.route("/take_photo")
def take_photo():
    output_path = "/storage/emulated/0/Pictures/photo.jpg"  # This is the same as ~/storage/shared/Pictures/photo.jpg

    # Make sure folder exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Take photo using termux-camera-photo
    ret = os.system(f"termux-camera-photo {output_path}")
    if ret != 0:
        return "Failed to run camera command", 500

    # Wait a bit for photo to save
    time.sleep(1)

    if os.path.exists(output_path):
        return send_file(output_path, mimetype="image/jpeg")
    else:
        return "Photo capture failed", 500

@app.route("/ping")
def ping():
    return "pong"

if __name__ == "__main__":
    # Listen on all interfaces so your PC can connect
    app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False)
