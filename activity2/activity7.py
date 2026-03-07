import serial
import serial.tools.list_ports
import sys
import time


def get_serial_connection():

    # CONFIGURATION: Replace 'COM3' with the actual port your Arduino is connected to.
    port = 'COM6' 
    baudrate = 9600
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)  # Short delay to allow Arduino serial buffer to stabilize
        return ser
    except serial.SerialException as e:
        print(f"Error: Could not open serial port {port}.")
        # ... Error handling logic ...
        sys.exit(1)

def main():
    ser = get_serial_connection()
    print("Connection established. Enter degrees (0-180) or 'exit' to quit.")

    while True:
        user_input = input("\nEnter Degrees: ").strip().lower()
        
        if user_input == 'exit':
            break

        try:
            val = int(user_input)
            if 0 <= val <= 180:
                ser.write(f"{val}\n".encode())
                print(f"Command successful: Moved servo to {val} degrees.")
            else:
                print("Validation Error: Please enter a value between 0 and 180.")
                
        except ValueError:
            print("Validation Error: Invalid input. Please enter a whole number.")

    ser.close()

if __name__ == "__main__":
    main()