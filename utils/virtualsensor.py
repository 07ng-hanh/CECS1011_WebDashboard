import asyncio
import json
import serial
import websockets
import time
from websockets.exceptions import ConnectionClosedError, ConnectionClosed

# --- CONFIGURATION ---
WS_ENDPOINT = "wss://cecs-project-warehousemgmt.westus2.cloudapp.azure.com/api/sensors/write-sensor-data"
API_KEY = "c2NyZWVuZHJlYW1tZWRpY2luZWx5aW5ndGhhbmttaW51dGVyb2FyZ2FyZGVuY29uZGk"

# Hardware settings
SERIAL_PORT = 'COM9'
BAUD_RATE = 115200    # ESP32 standard baud rate

async def send_real_sensor_data():
    ser = None
    
    # 1. Initialize the Serial connection with a retry loop
    while ser is None:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            # ESP32 auto-resets when serial opens; give it time to boot
            print(f"Waiting for ESP32 on {SERIAL_PORT} to initialize...")
            time.sleep(2) 
            ser.reset_input_buffer() 
            print("Serial connection established.")
        except Exception as e:
            print(f"Could not open {SERIAL_PORT}: {e}. Retrying in 5s...")
            await asyncio.sleep(5)

    headers = {"Authorization": API_KEY}

    while True:
        try:
            # 2. Connect to the Azure websocket
            async with websockets.connect(WS_ENDPOINT, additional_headers=headers) as websocket:
                print(f"Cloud Connection Active: {WS_ENDPOINT}")

                while True:
                    if ser.in_waiting > 0:
                        try:
                            # Read and decode line
                            raw_line = ser.readline().decode('utf-8', errors='ignore').strip()
                            
                            # Validation: Ensure the data contains our expect   ed keys
                            if all(key in raw_line for key in ["TEMP:", "HUM:", "CO2:"]):
                                # Parse format: TEMP:24.5,HUM:50.2,CO2:600
                                parts = {item.split(":")[0]: float(item.split(":")[1]) for item in raw_line.split(",")}
                                
                                payload = {
                                    "temperature": parts["TEMP"],
                                    "humidity": parts["HUM"],
                                    "co2": int(parts["CO2"])  # CO2 is usually an integer ppm
                                }

                                await websocket.send(json.dumps(payload))
                                print(f"SENT TO CLOUD -> Temp: {payload['temperature']}C, Hum: {payload['humidity']}%, CO2: {payload['co2']}ppm")

                        except (ValueError, IndexError) as parse_error:
                            print(f"Data Noise/Skip: {raw_line}")
                        except Exception as e:
                            print(f"Processing Error: {e}")

                    await asyncio.sleep(0.01) # High frequency polling

        except (ConnectionClosed, ConnectionClosedError, OSError) as e:
            print(f"Cloud Connection Lost: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Critical Bridge Error: {e}")
            await asyncio.sleep(3)

if __name__ == "__main__":
    try:
        asyncio.run(send_real_sensor_data())
    except KeyboardInterrupt:
        print("\nBridge stopped by user.")