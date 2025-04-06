import asyncio
import websockets
import json
import random
from datetime import datetime
import sys

class MedicalDevice:
    def __init__(self, patient_id, server_url="ws://localhost:5000"):
        self.patient_id = patient_id
        self.ws_url = f"{server_url}/ws/stream/{patient_id}"
        self.running = False
        
    def generate_data(self):
        """Generate simulated medical data"""
        return {
            "heart_rate": round(random.uniform(60, 100), 1),
            "blood_pressure_systolic": round(random.uniform(100, 140), 1),
            "blood_pressure_diastolic": round(random.uniform(60, 90), 1),
            "temperature": round(random.uniform(36.1, 37.8), 1),
            "oxygen_saturation": round(random.uniform(95, 100), 1),
            "respiratory_rate": round(random.uniform(12, 20), 1),
            "glucose_level": round(random.uniform(70, 140), 1),
            "ecg_voltage": round(random.uniform(-0.5, 1.5), 3),
            "brain_activity": round(random.uniform(8, 13), 2)
        }
    
    async def start_streaming(self):
        """Start streaming data to server"""
        self.running = True
        
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    print(f"Connected to {self.ws_url}")
                    
                    while self.running:
                        # Generate and send data
                        data = {
                            "patient_id": self.patient_id,
                            "sensor_data": self.generate_data(),
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        await ws.send(json.dumps(data))
                        response = await ws.recv()
                        print(f"Server response: {response}")
                        
                        # Wait 1 second before next reading
                        await asyncio.sleep(1)
                        
            except websockets.exceptions.ConnectionClosed:
                print("Connection lost. Attempting to reconnect...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Error: {str(e)}")
                await asyncio.sleep(5)
    
    def stop_streaming(self):
        """Stop streaming data"""
        self.running = False

async def main():
    if len(sys.argv) < 2:
        print("Usage: python simulate_device.py <patient_id>")
        return
        
    patient_id = int(sys.argv[1])
    device = MedicalDevice(patient_id)
    
    try:
        print(f"Starting medical device simulation for patient {patient_id}")
        await device.start_streaming()
    except KeyboardInterrupt:
        print("\nStopping simulation...")
        device.stop_streaming()

if __name__ == "__main__":
    asyncio.run(main())
