import asyncio
import json
import random
import websockets

# Configuration
WS_ENDPOINT = "ws://127.0.0.1:8000/api/sensors/write-sensor-data"
API_KEY = "c2NyZWVuZHJlYW1tZWRpY2luZWx5aW5ndGhhbmttaW51dGVyb2FyZ2FyZGVuY29uZGk="
INTERVAL_SECS = 1

async def send_sensor_data():
    # Define the headers for authentication
    headers = {
        "Authorization": API_KEY
    }

    try:
        # Connect to the websocket server
        async with websockets.connect(WS_ENDPOINT, additional_headers=headers) as websocket:
            print(f"Connected to {WS_ENDPOINT}")

            while True:
                # Generate random sensor data
                data = {
                    "temperature": round(random.uniform(-20, -10), 2),
                    "humidity": round(random.uniform(80, 95), 2),
                    "co2": round(random.uniform(300, 500), 2)
                }

                # Convert dictionary to JSON string and send
                json_payload = json.dumps(data)
                await websocket.send(json_payload)
                
                print(f"Sent: {json_payload}")

                # Wait for the specified interval
                await asyncio.sleep(INTERVAL_SECS)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(send_sensor_data())