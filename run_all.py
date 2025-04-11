import subprocess
import asyncio
import websockets
import json
from datetime import datetime
import os
import time
import fastapi
import sys

# Function to start the WebSocket server
def start_websocket_server():
    print("[INFO] Starting WebSocket server...")
    python_exec=sys.executable
    print(f"[DEBUG] Using Python executable: {python_exec}")
    return subprocess.Popen([python_exec, "websocket_server.py"])

# Function to start the Streamlit app
def start_streamlit_app():
    print("[INFO] Starting Streamlit app...")
    return subprocess.Popen(["streamlit", "run", "main.py"])

class ArduinoDevice:
    def __init__(self, patient_id, arduino_url, server_url="ws://localhost:5000"):
        self.patient_id = patient_id
        self.arduino_url = arduino_url  # Arduino WebSocket or HTTP endpoint
        self.server_url = f"{server_url}/ws/stream/{patient_id}"
        self.running = False

    async def fetch_data_from_arduino(self):
        """Fetch real data from Arduino via WebSocket"""
        try:
            async with websockets.connect(self.arduino_url) as arduino_ws:
                print(f"[INFO] Connected to Arduino at {self.arduino_url}")
                while self.running:
                    # Receive data from Arduino
                    raw_data = await arduino_ws.recv()
                    print(f"[INFO] Data from Arduino: {raw_data}")
                    return json.loads(raw_data)  # Ensure Arduino sends JSON data
        except Exception as e:
            print(f"[ERROR] Failed to fetch data from Arduino: {e}")
            await asyncio.sleep(5)
            return None

    async def start_streaming(self):
        """Stream real data from Arduino to the WebSocket server"""
        self.running = True

        while self.running:
            try:
                # Connect to the WebSocket server
                async with websockets.connect(self.server_url) as server_ws:
                    print(f"[INFO] Connected to WebSocket server at {self.server_url}")

                    while self.running:
                        # Fetch data from Arduino
                        arduino_data = await self.fetch_data_from_arduino()
                        if arduino_data is None:
                            continue

                        # Prepare data to send to the WebSocket server
                        data = {
                            "patient_id": self.patient_id,
                            "sensor_data": arduino_data,
                            "timestamp": datetime.now().isoformat()
                        }

                        # Send data to the WebSocket server
                        await server_ws.send(json.dumps(data))
                        response = await server_ws.recv()
                        print(f"[INFO] Server response: {response}")

                        # Wait 1 second before the next reading
                        await asyncio.sleep(1)

            except websockets.exceptions.ConnectionClosed:
                print("[WARN] Connection to server lost. Reconnecting...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"[ERROR] {str(e)}")
                await asyncio.sleep(5)

    def stop_streaming(self):
        """Stop streaming data"""
        self.running = False

def get_patient_id_from_file():
    """Read patient_id from the shared file"""
    try:
        with open("shared_patient_id.json", "r") as f:
            data = json.load(f)
            return data.get("patient_id")
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None

async def main():
    # Start WebSocket server and Streamlit app
    websocket_process = start_websocket_server()
    streamlit_process = start_streamlit_app()

    # Wait for the WebSocket server and Streamlit app to initialize
    await asyncio.sleep(5)

    # Arduino device configuration
    arduino_url = "ws://192.168.1.100:81"  # Replace with your Arduino's WebSocket URL
    device = None

    try:
        while True:
            # Dynamically fetch patient_id from the shared file
            patient_id = get_patient_id_from_file()
            if patient_id:
                print(f"[INFO] Detected patient_id: {patient_id}")

                # Start streaming if a patient_id is detected and device is not running
                if not device or device.patient_id != patient_id:
                    if device:
                        device.stop_streaming()
                    device = ArduinoDevice(patient_id, arduino_url)
                    await device.start_streaming()

            await asyncio.sleep(2)  # Check for updates every 2 seconds

    except KeyboardInterrupt:
        print("\n[INFO] Stopping all processes...")
        if device:
            device.stop_streaming()
        websocket_process.terminate()
        streamlit_process.terminate()

if __name__ == "__main__":
    asyncio.run(main())