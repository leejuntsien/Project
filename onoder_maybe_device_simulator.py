
import asyncio
import websockets
import json
import random
from datetime import datetime
import sys
import argparse

class MedicalDevice:
    def __init__(self, patient_id, server_url="ws://localhost:5000", wifi_address=None):
        self.patient_id = patient_id
        self.ws_url = f"{server_url}/ws/stream/{patient_id}"
        self.running = False
        self.wifi_address = wifi_address
        
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
                connection_url = self.ws_url
                print(f"Connecting to {connection_url}")
                
                if self.wifi_address:
                    print(f"Using WiFi address: {self.wifi_address}")
                    # In real implementation, you would configure the WiFi here
                    # For ESP32, this would involve network configuration
                
                async with websockets.connect(connection_url) as ws:
                    print(f"Connected to {connection_url}")
                    
                    while self.running:
                        # Generate and send data
                        data = {
                            "patient_id": self.patient_id,
                            "sensor_data": self.generate_data(),
                            "timestamp": datetime.now().isoformat(),
                            "device_info": {
                                "wifi_address": self.wifi_address,
                                "device_type": "ESP32_SIMULATOR"
                            }
                        }
                        
                        await ws.send(json.dumps(data))
                        try:
                            response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                            print(f"Server response: {response}")
                        except asyncio.TimeoutError:
                            print("Server response timeout, but continuing operation")
                        
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
    parser = argparse.ArgumentParser(description='Medical Device Simulator')
    parser.add_argument('patient_id', type=int, help='Patient ID')
    parser.add_argument('--server', '-s', type=str, default='ws://localhost:5000', 
                       help='WebSocket server URL (default: ws://localhost:5000)')
    parser.add_argument('--wifi', '-w', type=str, 
                       help='WiFi address to connect to (for ESP32 configuration)')
    
    args = parser.parse_args()
    
    device = MedicalDevice(
        patient_id=args.patient_id,
        server_url=args.server,
        wifi_address=args.wifi
    )
    
    try:
        print(f"Starting medical device simulation for patient {args.patient_id}")
        if args.wifi:
            print(f"Using WiFi configuration: {args.wifi}")
        await device.start_streaming()
    except KeyboardInterrupt:
        print("\nStopping simulation...")
        device.stop_streaming()

if __name__ == "__main__":
    asyncio.run(main())
