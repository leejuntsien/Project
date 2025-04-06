import streamlit as st
from backend_patient_info import get_patient_data
from utils.security import require_admin_auth, is_admin_authenticated

st.set_page_config(page_title="Patient Data", layout="wide")

# Check authentication
if not is_admin_authenticated():
    st.error("⚠️ Access Denied: Admin authentication required")
    st.warning("Please log in to access patient data.")
    if st.button("Go to Login"):
        st.switch_page("pages/_admin_auth.py")
    st.stop()

# Get patient ID from URL parameter
patient_id = st.query_params.get("id")

if not patient_id:
    st.warning("No patient ID specified")
    if st.button("← Back to Patient List"):
        st.switch_page("pages/_admin_patient_info.py")
    st.stop()

st.title(f"Patient Data - {patient_id}")

# Get patient data
patient_data = get_patient_data(patient_id)

if not patient_data:
    st.info("No data available for this patient")
else:
    # Create a table of patient data
    st.write("### Data Records")
    
    # Get column names from your database schema
    columns = ["Timestamp", "Temperature", "Heart Rate", "Blood Pressure", "SpO2"]  # Adjust based on your schema
    
    # Create header
    cols = st.columns(len(columns))
    for i, col in enumerate(columns):
        cols[i].write(f"**{col}**")
    
    # Display data rows
    for record in patient_data:
        cols = st.columns(len(columns))
        for i, value in enumerate(record):
            cols[i].write(value)

# Navigation buttons
col1, col2 = st.columns(2)
if col1.button("← Back to Patient List"):
    st.switch_page("pages/_admin_patient_info.py")
if col2.button("🔄 Refresh Data"):
    st.rerun()