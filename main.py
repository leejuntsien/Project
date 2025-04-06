import streamlit as st
from backend_auth import get_db_connection
from dotenv import load_dotenv
import os

# Load .env from common locations
env_files = [
    os.path.join('.env', 'FYP_webapp.env'),
    '.env',
    '../.env',
]

for env_file in env_files:
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"[INFO] Loaded environment variables from {env_file}")
        break
else:
    print("[WARN] No .env found. Falling back to system env.")
    
st.set_page_config(page_title="Patient Management System", layout="centered")

st.title("Patient Management System")

import base64

# Read image and encode
with open("frontend/static/puppy_attack_doctor.png", "rb") as f:
    data = f.read()
    encoded = base64.b64encode(data).decode()

# Animated HTML display
st.markdown(
    f"""
    <div style="text-align:center;">
        <img src="data:image/png;base64,{encoded}" alt="Puppy Attack!" width="400" 
             style="animation: wiggle 1s ease-in-out infinite;">
        <p style="font-size:20px; color: red;"><strong>HIPAA breach imminent!</strong></p>
    </div>

    <style>
    @keyframes wiggle {{
      0% {{ transform: rotate(0deg); }}
      25% {{ transform: rotate(2deg); }}
      50% {{ transform: rotate(-2deg); }}
      75% {{ transform: rotate(2deg); }}
      100% {{ transform: rotate(0deg); }}
    }}
    </style>
    """,
    unsafe_allow_html=True
)


st.markdown("**[Project Introduction Placeholder]**")

col1, col2 = st.columns([3, 1])

with col1:
    st.page_link("pages/patient_auth.py", label="Start (User)", icon="🧑")
with col2:
    st.page_link("pages/_admin_auth.py", label="Admin", icon="🔑")



if st.button("connection"):
    conn = get_db_connection()
conn = get_db_connection()
if conn:
    st.success("Database connection successful!")
    conn.close()
else:
    st.error("Database connection failed!")
