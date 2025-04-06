import subprocess
import sys
import os
from dotenv import load_dotenv

load_dotenv()

def run_servers():
    try:
        # Start Flask API server
        api_process = subprocess.Popen(
            ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"],
            env=dict(os.environ, FLASK_APP="api/server.py", FLASK_ENV="development")
        )
        
        # Start Streamlit app
        streamlit_process = subprocess.Popen(
            ["streamlit", "run", "Home.py", "--server.port=8501"]
        )
        
        print("🚀 Servers started successfully!")
        print("📡 Flask API running on http://localhost:5000")
        print("🌐 Streamlit app running on http://localhost:8501")
        
        # Wait for processes to complete
        api_process.wait()
        streamlit_process.wait()
        
    except KeyboardInterrupt:
        print("\n⚠️ Shutting down servers...")
        api_process.terminate()
        streamlit_process.terminate()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_servers()
