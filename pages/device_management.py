import streamlit as st
import requests
from datetime import datetime
import json
import os
from dotenv import load_dotenv
import socketio
from auth.security import require_jwt

# Load environment variables
load_dotenv()

API_URL = os.getenv('API_URL', 'http://localhost:5000')
sio = socketio.Client()

st.set_page_config(page_title="Device Management", layout="wide")

@require_jwt
def init_page():
    st.title("Device Management")
    
    # Device Registration Section
    st.header("Register New Device")
    with st.form("device_registration"):
        device_id = st.text_input("Device ID")
        patient_id = st.number_input("Patient ID", min_value=1)
        secret = st.text_input("Device Secret", type="password")
        
        if st.form_submit_button("Register Device"):
            try:
                response = requests.post(
                    f"{API_URL}/api/device/auth",
                    json={
                        "device_id": device_id,
                        "patient_id": patient_id,
                        "secret": secret
                    },
                    headers={"Authorization": f"Bearer {st.session_state.jwt_token}"}
                )
                
                if response.status_code == 200:
                    st.success("Device registered successfully!")
                else:
                    st.error(f"Error: {response.json().get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")

    # Active Devices Section
    st.header("Active Devices")
    if st.button("Refresh Devices"):
        try:
            response = requests.get(
                f"{API_URL}/api/devices",
                headers={"Authorization": f"Bearer {st.session_state.jwt_token}"}
            )
            if response.status_code == 200:
                devices = response.json()['devices']
                if devices:
                    for device in devices:
                        with st.expander(f"Device: {device}"):
                            st.write("Status: Active")
                            if st.button("Disconnect", key=f"disconnect_{device}"):
                                # Implement device disconnection logic
                                pass
                else:
                    st.info("No active devices")
        except Exception as e:
            st.error(f"Error fetching devices: {str(e)}")

    # Live Data Stream
    st.header("Live Data Stream")
    if 'data_stream' not in st.session_state:
        st.session_state.data_stream = []

    # WebSocket connection
    if 'ws_connected' not in st.session_state:
        st.session_state.ws_connected = False

    def on_connect():
        st.session_state.ws_connected = True

    def on_disconnect():
        st.session_state.ws_connected = False

    def on_new_data(data):
        st.session_state.data_stream.append(data)
        if len(st.session_state.data_stream) > 100:  # Keep only last 100 readings
            st.session_state.data_stream.pop(0)

    if not st.session_state.ws_connected:
        try:
            sio.connect(API_URL)
            sio.on('connect', on_connect)
            sio.on('disconnect', on_disconnect)
            sio.on('new_data', on_new_data)
        except Exception as e:
            st.error(f"WebSocket connection error: {str(e)}")

    # Display live data
    if st.session_state.data_stream:
        for data in reversed(st.session_state.data_stream[-10:]):  # Show last 10 readings
            with st.expander(f"Data from Device {data['device_id']} at {data['timestamp']}"):
                st.json(data['sensor_data'])

if __name__ == "__main__":
    init_page()
