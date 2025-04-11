
import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
from backend_auth import get_db_connection
from datetime import datetime
import base64
from io import BytesIO
import time

# Page configuration with wider layout
st.set_page_config(page_title="Patient Dashboard", layout="wide")

# Apply custom CSS
with open("frontend/static/enhanced_style.css", "r") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Helper function to add a background image
def add_bg_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    
    bg_image = f"""
    <div class="background-container" 
         style="background-image: url(data:image/png;base64,{encoded_string})">
    </div>
    """
    st.markdown(bg_image, unsafe_allow_html=True)

# Try to add the background image
try:
    add_bg_image("static/puppy_attack_doctor.png")
except Exception as e:
    st.write("")  # Silent fail for background image

# Check authentication
if "patient_id" not in st.session_state:
    st.error("Please log in first!")
    st.stop()

patient_id = st.session_state["patient_id"]
username = st.session_state["username"]

# Dashboard header with improved styling
st.markdown(f"""
<div style="display: flex; align-items: center; margin-bottom: 1rem;">
    <h1 style="margin: 0; flex-grow: 1;">🩺 Patient Dashboard</h1>
    <div style="background-color: #f8f9fa; padding: 0.5rem 1rem; border-radius: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
        <span style="font-weight: 600; color: #3498db;"> 🧟‍♂️ {username}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Auto-refresh every 7 seconds
refresh_interval = 7
st_autorefresh(interval=refresh_interval * 1000, key="dashboard_refresh")

# Function to start a new trial
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

# Trial Controls in an attractive card
st.markdown("""
<div class="card">
    <h2>🎯 Trial Controls</h2>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    if 'current_trial_id' not in st.session_state:
        if st.button("🟢 Start New Trial", use_container_width=True):
            with st.spinner("Initializing trial..."):
                if start_trial():
                    st.success("Trial started! Redirecting to trial page...")
                    time.sleep(1)  # Small delay for better UX
                    st.switch_page("pages/new_trial.py")

with col2:
    # Show trial status
    if 'current_trial_id' in st.session_state:
        st.markdown(f"""
        <div class="status-active">
            Trial #{st.session_state.current_trial_id} in Progress
        </div>
        """, unsafe_allow_html=True)
        if st.button("📝 Continue Trial", use_container_width=True):
            st.switch_page("pages/new_trial.py")
    else:
        st.markdown("""
        <div class="status-inactive">
            No Active Trial
        </div>
        """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # Close the card div

st.divider()

# Function to get live data
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

# Live Data Section
st.markdown(f"""
<div class="card live-data">
    <h2>📡 Live Data Stream</h2>
    <p>Data refreshes every {refresh_interval} seconds</p>
</div>
""", unsafe_allow_html=True)

# Get and display live data
df = get_live_data(patient_id)

if df is not None and not df.empty:
    # Get numerical columns
    param_columns = [col for col in df.columns if col != 'timestamp' and pd.api.types.is_numeric_dtype(df[col])]
    
    # Create dashboard layout with columns for charts
    chart_cols = st.columns(min(2, len(param_columns)))
    
    # Create line plots in columns
    for i, param in enumerate(param_columns):
        col_idx = i % len(chart_cols)
        with chart_cols[col_idx]:
            fig = px.line(
                df,
                x='timestamp',
                y=param,
                title=f"{param.replace('_', ' ').title()}"
            )
            
            fig.update_layout(
                height=250,
                margin=dict(l=0, r=0, t=40, b=0),
                xaxis_title=None,
                yaxis_title=None,
                showlegend=False,
                xaxis=dict(showgrid=True),
                yaxis=dict(showgrid=True),
                plot_bgcolor='rgba(255,255,255,0.9)',
                paper_bgcolor='rgba(255,255,255,0)',
                font=dict(color='#2c3e50'),
                title_font=dict(size=18, family='Arial', color='#2980b9')
            )
            
            # Add rolling average
            fig.add_scatter(
                x=df['timestamp'],
                y=df[param].rolling(window=5).mean(),
                name=f"{param} (5s avg)",
                line=dict(color='#e74c3c', width=2, dash='dot')
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add metric summary
            latest_value = df[param].iloc[0] if not df.empty else "N/A"
            avg_value = df[param].mean() if not df.empty else "N/A"
            
            metric_cols = st.columns(2)
            metric_cols[0].metric(
                label=f"Current {param.replace('_', ' ').title()}", 
                value=f"{latest_value:.1f}" if isinstance(latest_value, (int, float)) else latest_value
            )
            metric_cols[1].metric(
                label=f"Average {param.replace('_', ' ').title()}", 
                value=f"{avg_value:.1f}" if isinstance(avg_value, (int, float)) else avg_value
            )
else:
    st.info("No live data available. Waiting for sensor readings...")
    
    # Add a placeholder with animated dots
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <div style="display: inline-block; margin-bottom: 1rem;">
            <svg width="50" height="50" viewBox="0 0 24 24" style="animation: spin 2s linear infinite;">
                <path fill="#3498db" d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z" opacity=".25"/>
                <path fill="#3498db" d="M12,4a8,8,0,0,1,7.89,6.7A1.53,1.53,0,0,0,21.38,12h0a1.5,1.5,0,0,0,1.48-1.75,11,11,0,0,0-21.72,0A1.5,1.5,0,0,0,2.62,12h0a1.53,1.53,0,0,0,1.49-1.3A8,8,0,0,1,12,4Z">
                    <animateTransform attributeName="transform" dur="0.75s" repeatCount="indefinite" type="rotate" values="0 12 12;360 12 12"/>
                </path>
            </svg>
        </div>
        <p style="color: #7f8c8d; font-style: italic;">Waiting for data to stream from your sensors...</p>
    </div>
    <style>
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    </style>
    """, unsafe_allow_html=True)

st.divider()

# Bottom navigation bar
st.markdown("""
<div style="display: flex; gap: 10px; margin-top: 1rem; justify-content: center;">
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("📊 Historic Data", use_container_width=True):
        st.switch_page("pages/historic_data.py")

with col2:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

with col3:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.success("Logged out successfully!")
        st.switch_page("main.py")

st.markdown("</div>", unsafe_allow_html=True)  # Close the flex container

# Add session info in footer
st.markdown(f"""
<div style="position: fixed; bottom: 0; left: 0; right: 0; background-color: #f8f9fa; 
            padding: 0.5rem; text-align: center; font-size: 0.8rem; color: #7f8c8d; border-top: 1px solid #ecf0f1;">
    Patient ID: {patient_id} | Session started: {datetime.now().strftime('%Y-%m-%d %H:%M')}
</div>
""", unsafe_allow_html=True)
