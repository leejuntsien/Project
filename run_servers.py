import subprocess
import sys
import os
from dotenv import load_dotenv

load_dotenv()

def run_servers():
    try:
        # Start FastAPI server with SSL
        api_process = subprocess.Popen([
            "uvicorn",
            "backend.app:app",
            "--host=0.0.0.0",
            "--port=5000",
            "--ssl-keyfile=/app/ssl/server.key",
            "--ssl-certfile=/app/ssl/server.crt"
        ])
        
        # Start Streamlit app with SSL
        streamlit_process = subprocess.Popen([
            "streamlit",
            "run",
            "Home.py",
            "--server.port=8501",
            "--server.sslCertFile=/app/ssl/server.crt",
            "--server.sslKeyFile=/app/ssl/server.key"
        ])
        
        print("🚀 Servers started successfully!")
        print("🔒 FastAPI running on https://localhost:5000")
        print("🔒 Streamlit app running on https://localhost:8501")
        
        # Wait for processes to complete
        api_process.wait()
        streamlit_process.wait()
        
    except KeyboardInterrupt:
        print("\n⚠️ Shutting down servers...")
        api_process.terminate()
        streamlit_process.terminate()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_servers()
