import serial
import time

# ⚠️ CHANGE THIS IF YOUR PORT IS DIFFERENT
arduino = serial.Serial('COM6', 9600, timeout=1)

time.sleep(2)

print("AI SYSTEM RUNNING...\n")

while True:
    try:
        data = arduino.readline().decode().strip()

        if data == "":
            continue

        speed = float(data)

        # =========================
        # AI DECISION (YOUR SYSTEM)
        # =========================
        if speed < 2.0:
            status = "SAFE 🟢"
        elif speed < 3.0:
            status = "WARNING 🟡"
        else:
            status = "DANGER 🔴"

        print(f"Speed: {speed:.2f} m/s | {status}")

    except ValueError:
        print("Invalid data received...")
        time.sleep(0.5)

    except Exception as e:
        print("Connection error:", e)
        time.sleep(1)