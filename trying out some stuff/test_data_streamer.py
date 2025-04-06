
import websocket
import json
import time
import random
import threading
import argparse
from datetime import datetime
import sys

class DataStreamer:
    def __init__(self, patient_id, ws_url="ws://localhost:5000/socket.io", use_ssl=False):
        self.patient_id = patient_id
        
        # Set protocol based on SSL setting
        protocol = "wss" if use_ssl else "ws"
        
        # Allow for flexible URL patterns (modify this to match your server)
        # Common Flask-SocketIO patterns:
        # - /socket.io/ (default Flask-SocketIO endpoint)
        # - /ws (custom WebSocket endpoint)
        if ws_url.endswith('/'):
            self.ws_url = ws_url
        else:
            self.ws_url = f"{ws_url}/"
            
        # Ensure protocol is set correctly
        if not self.ws_url.startswith(("ws://", "wss://")):
            self.ws_url = f"{protocol}://{self.ws_url}"
            
        print(f"Connecting to: {self.ws_url}")
        
        self.ws = None
        self.is_streaming = False
        self.parameters = [
            "heart_rate",
            "blood_pressure_systolic",
            "blood_pressure_diastolic",
            "temperature",
            "oxygen_saturation",
            "respiratory_rate",
            "glucose_level",
            "ecg_voltage",
            "brain_activity"
        ]

    def generate_data(self):
        """Generate realistic medical data"""
        return {
            "heart_rate": random.uniform(60, 100),
            "blood_pressure_systolic": random.uniform(100, 140),
            "blood_pressure_diastolic": random.uniform(60, 90),
            "temperature": random.uniform(36.1, 37.8),
            "oxygen_saturation": random.uniform(95, 100),
            "respiratory_rate": random.uniform(12, 20),
            "glucose_level": random.uniform(70, 140),
            "ecg_voltage": random.uniform(-0.5, 1.5),
            "brain_activity": random.uniform(8, 13)  # Alpha waves Hz
        }

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            print(f"Received: {data}")
        except:
            print(f"Received: {message}")

    def on_error(self, ws, error):
        print(f"Error: {error}")
        
        # More helpful error messages based on common issues
        if "10061" in str(error):
            print("\nServer connection refused. Please make sure:")
            print("1. Your WebSocket server is running")
            print(f"2. It's accepting connections at {self.ws_url}")
            print("3. No firewall is blocking the connection")
        elif "404" in str(error):
            print("\nEndpoint not found (404). Please check:")
            print("1. The WebSocket endpoint on your server")
            print("2. Try using the default Socket.IO endpoint: ws://localhost:5000/socket.io/")
            print("3. Check server logs to see what endpoints are registered")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"Connection closed{': ' + close_msg if close_msg else ''}")
        self.is_streaming = False

    def on_open(self, ws):
        print(f"Connection opened to {self.ws_url}")
        self.is_streaming = True
        
        def run():
            try:
                while self.is_streaming:
                    # Include patient_id in the data for routing on the server side
                    data = {
                        "patient_id": self.patient_id,
                        "sensor_data": self.generate_data(),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    json_data = json.dumps(data)
                    print(f"Sending data: {json_data[:60]}...")  # Print truncated data
                    ws.send(json_data)
                    time.sleep(1)  # Send data every second
            except Exception as e:
                print(f"Error in data streaming thread: {e}")
                self.stop_streaming()
            
        threading.Thread(target=run).start()

    def start_streaming(self):
        """Start streaming data"""
        websocket.enableTrace(True)  # For debugging
        
        # Create WebSocket with proper error handling
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open
            )
            self.ws.run_forever()
        except Exception as e:
            print(f"Failed to create WebSocket connection: {e}")

    def stop_streaming(self):
        """Stop streaming data"""
        self.is_streaming = False
        if self.ws:
            self.ws.close()

if __name__ == "__main__":
    # Set up argument parser for more options
    parser = argparse.ArgumentParser(description='Stream medical data for a patient')
    parser.add_argument('patient_id', type=int, help='Patient ID to stream data for')
    parser.add_argument('--url', type=str, default='ws://localhost:5000/socket.io',
                        help='WebSocket server URL (default: ws://localhost:5000/socket.io)')
    parser.add_argument('--ssl', action='store_true', help='Use secure WebSocket (wss://)')
    parser.add_argument('--interval', type=float, default=1.0, 
                        help='Data sending interval in seconds (default: 1.0)')
    
    try:
        args = parser.parse_args()
    except SystemExit:
        # If argument parsing fails, provide a simpler interface
        if len(sys.argv) < 2:
            print("Usage: python test_data_streamer.py <patient_id> [--url SERVER_URL] [--ssl] [--interval SECONDS]")
            sys.exit(1)
        args = argparse.Namespace()
        args.patient_id = int(sys.argv[1])
        args.url = 'ws://localhost:5000/socket.io'
        args.ssl = False
        args.interval = 1.0
    
    print(f"Starting data stream for patient {args.patient_id}")
    print(f"Server URL: {args.url}")
    print(f"Using SSL: {args.ssl}")
    
    streamer = DataStreamer(args.patient_id, args.url, args.ssl)
    
    try:
        streamer.start_streaming()
    except KeyboardInterrupt:
        print("\nStopping data stream...")
        streamer.stop_streaming()
