import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
from backend_auth import get_db_connection
from datetime import datetime

st.set_page_config(page_title="Patient Dashboard", layout="wide")
st.title("🩺 Patient Dashboard")

# Ensure user is logged in
if "patient_id" not in st.session_state:
    st.error("Please log in first!")
    st.stop()

patient_id = st.session_state["patient_id"]
username = st.session_state["username"]

# Trial Controls
st.subheader("🎯 Trial Controls")
col1, col2 = st.columns(2)

def start_trial():
    """
    Start a new trial for the current patient.
    This function creates a new trial record but doesn't affect the rolling data collection.
    The WebSocket server will automatically start saving data to trial_temp when a trial is active.
    """
    conn = get_db_connection()
    if not conn:
        st.error("Could not connect to database")
        return False
        
    try:
        with conn.cursor() as cursor:
            # Check if there's already an active trial
            cursor.execute("""
                SELECT trial_id 
                FROM patient_trials 
                WHERE patient_id = %s AND end_time IS NULL
                ORDER BY start_time DESC 
                LIMIT 1
            """, (st.session_state.patient_id,))
            
            existing_trial = cursor.fetchone()
            if existing_trial:
                # There's already an active trial
                trial_id = existing_trial[0]
                st.warning(f"You already have an active trial (#{trial_id}). Continuing with this trial.")
                st.session_state.current_trial_id = trial_id
                return trial_id
            
            # Create a new trial record
            cursor.execute("""
                INSERT INTO patient_trials (patient_id, start_time, notes)
                VALUES (%s, NOW(), %s)
                RETURNING trial_id
            """, (st.session_state.patient_id, "Trial started from dashboard"))
            
            # Get the new trial ID
            trial_id = cursor.fetchone()[0]
            
            # Store the trial ID in session state
            st.session_state.current_trial_id = trial_id
            
            # Note: We don't need to initialize trial_data here because
            # the data is continuously collected in the trial_temp table
            # by the WebSocket server when a trial is active
            
            conn.commit()
            return trial_id
            
    except Exception as e:
        st.error(f"Error starting trial: {e}")
        st.exception(e)  # Show full traceback for debugging
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


with col1:
    if 'current_trial_id' not in st.session_state:
        if st.button("🟢 Start New Trial", use_container_width=True):
            if start_trial():
                st.success("Trial started! Redirecting to trial page...")
                st.switch_page("pages/new_trial.py")

with col2:
    # Show trial status
    if 'current_trial_id' in st.session_state:
        st.success(f"Trial #{st.session_state.current_trial_id} in Progress")
        if st.button("📝 Continue Trial", use_container_width=True):
            st.switch_page("pages/new_trial.py")
    else:
        st.info("No Active Trial")

st.divider()

# Live Data Monitoring
st.subheader(f"📡 Live Data Stream - {username}")

# Auto-refresh every 2 seconds
st_autorefresh(interval=7000, key="live_data_refresh")

def get_live_data(patient_id, limit=60):
    """Get live streaming data"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT sensor_data, timestamp 
                FROM live_patient_data 
                WHERE patient_id = %s 
                ORDER BY timestamp DESC 
                LIMIT %s
            """, (patient_id, limit))
            rows = cursor.fetchall()
            
            if not rows:
                return None
                
            data = []
            for row in rows:
                sensor_data, timestamp = row
                entry = {"timestamp": timestamp, **sensor_data}
                data.append(entry)
            
            return pd.DataFrame(data)
            
    except Exception as e:
        st.error(f"Error fetching live data: {str(e)}")
        return None
    finally:
        conn.close()

# Get and display live data
df = get_live_data(patient_id)

if df is not None and not df.empty:
    # Get numerical columns
    param_columns = [col for col in df.columns if col != 'timestamp' and pd.api.types.is_numeric_dtype(df[col])]
    
    # Create line plots
    for param in param_columns:
        fig = px.line(
            df,
            x='timestamp',
            y=param,
            title=f"{param.replace('_', ' ').title()}"
        )
        
        fig.update_layout(
            height=250,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis_title=None,
            yaxis_title=None,
            showlegend=False,
            xaxis=dict(showgrid=True),
            yaxis=dict(showgrid=True)
        )
        
        # Add rolling average
        fig.add_scatter(
            x=df['timestamp'],
            y=df[param].rolling(window=5).mean(),
            name=f"{param} (5s avg)",
            line=dict(color='red', width=1, dash='dot')
        )
        
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No live data available. Waiting for sensor readings...")

st.divider()

if st.button ("Historic Data"):
    st.switch_page("pages/historic_data.py")

# **Logout Button (Bottom)**
if st.sidebar.button("🚪 Logout"):
    st.session_state.clear()
    st.success("Logged out successfully!")
    st.switch_page("main.py")
