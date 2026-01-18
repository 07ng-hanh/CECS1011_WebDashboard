import asyncio
import json
import random
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosed, InvalidURI

# Configuration
WS_ENDPOINT = "ws://127.0.0.1:8000/api/sensors/write-sensor-data"
API_KEY = "c2NyZWVuZHJlYW1tZWRpY2luZWx5aW5ndGhhbmttaW51dGVyb2FyZ2FyZGVuY29uZGk="
INTERVAL_SECS = 1

async def send_sensor_data():
    while True:
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
        except ConnectionClosed as e:
            print(f"Connection closed: {e}")
            print("Retrying...")
            await asyncio.sleep(0.5)
        except InvalidURI as e:
            print(f"Invalid WebSocket URI: {e}")
            return
        except ConnectionClosedError as e:
            print(f"Connection closed unexpectedly: code={e.code}, reason={e.reason}")
            print("Retrying...")
            await asyncio.sleep(0.5)
        except OSError as e:
            print(f"Network error: {e}")
            print("Retrying...")
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            print("Retrying...")
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(send_sensor_data())