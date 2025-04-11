
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import json
from backend_auth import get_db_connection
import base64
import time

# Page configuration with wider layout
st.set_page_config(page_title="Trial Recording", layout="wide")

# Apply custom CSS
with open("frontend/static/enhanced_style.css", "r") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Helper function to add a background image
def add_bg_image():
    # Creating an abstract pattern background
    bg_html = """
    <style>
    .stApp {
        background-image: linear-gradient(to bottom, rgba(245, 247, 250, 0.95), rgba(245, 247, 250, 0.95)), 
                          url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M11 18c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm48 25c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm-43-7c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm63 31c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM34 90c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm56-76c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM12 86c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm28-65c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm23-11c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-6 60c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm29 22c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zM32 63c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm57-13c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-9-21c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM60 91c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM35 41c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM12 60c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2z' fill='%233498db' fill-opacity='0.05' fill-rule='evenodd'/%3E%3C/svg%3E");
    }
    </style>
    """
    st.markdown(bg_html, unsafe_allow_html=True)

# Add the background pattern
add_bg_image()

# Ensure user is logged in
if "patient_id" not in st.session_state:
    st.error("Please log in first!")
    st.stop()

patient_id = st.session_state["patient_id"]
trial_id = st.session_state.get("current_trial_id")

if not trial_id:
    st.error("No active trial! Please start a trial from the dashboard.")
    
    # Add a redirect button
    st.markdown("""
    <div style="text-align: center; margin-top: 2rem;">
        <p>Return to the dashboard to start a new trial</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Go to Dashboard", use_container_width=True):
        st.switch_page("pages/patient_dashboard.py")
    
    st.stop()

# Add attractive header
st.markdown(f"""
<div style="display: flex; align-items: center; margin-bottom: 1rem;">
    <div style="flex-grow: 1;">
        <h1 style="margin: 0;">📝 Trial Recording</h1>
        <p style="margin: 0; color: #7f8c8d;">Collecting real-time health data</p>
    </div>
    <div style="background-color: #2ecc71; color: white; padding: 0.5rem 1rem; border-radius: 20px; font-weight: bold;">
        Trial #{trial_id} Active
    </div>
</div>
""", unsafe_allow_html=True)

# Auto-refresh for live data
refresh_interval = 7
st_autorefresh(interval=refresh_interval * 1000, key="trial_refresh")

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Function implementations
def get_live_data():
    """Get the most recent data from live_patient_data table"""
    # ... keep existing code
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
                LIMIT 60
            """, (patient_id,))
            rows = cursor.fetchall()
            
            if not rows:
                return None
                
            # Create separate lists for each column to avoid mixed types
            timestamps = []
            sensor_values = {}
            
            for row in rows:
                sensor_data, timestamp = row
                
                # Convert timestamp to datetime
                if isinstance(timestamp, datetime):
                    timestamps.append(timestamp)
                else:
                    try:
                        timestamps.append(pd.to_datetime(timestamp))
                    except:
                        # Skip invalid timestamps
                        continue
                
                # Parse sensor_data
                if isinstance(sensor_data, str):
                    try:
                        sensor_data = json.loads(sensor_data)
                    except json.JSONDecodeError:
                        # Skip invalid JSON data
                        continue
                
                # Extract numeric values from sensor_data
                if isinstance(sensor_data, dict):
                    for key, value in sensor_data.items():
                        # Skip any key named "Rows" to avoid conflicts
                        if key in ["Rows", "Index", "__index_level_0__"]:
                            continue
                            
                        # Try to convert to float
                        try:
                            if isinstance(value, (int, float)):
                                float_value = float(value)
                            elif isinstance(value, str) and value.replace('.', '', 1).isdigit():
                                float_value = float(value)
                            else:
                                continue  # Skip non-numeric values
                                
                            # Initialize list for this key if it doesn't exist
                            if key not in sensor_values:
                                sensor_values[key] = [np.nan] * len(timestamps)
                            
                            # Ensure lists are the same length by padding with NaN
                            while len(sensor_values[key]) < len(timestamps):
                                sensor_values[key].append(np.nan)
                            
                            # Add the value
                            sensor_values[key][-1] = float_value
                            
                        except (ValueError, TypeError):
                            # Skip if conversion fails
                            pass
            
            if not timestamps:
                return None
                
            # Create a DataFrame with explicit dtypes
            data = {'timestamp': timestamps}
            for key, values in sensor_values.items():
                # Ensure all lists are the same length
                while len(values) < len(timestamps):
                    values.append(np.nan)
                data[key] = values
                
            df = pd.DataFrame(data)
            
            # Sort by timestamp
            df = df.sort_values('timestamp')
            
            return df
            
    except Exception as e:
        st.error(f"Error fetching live data: {str(e)}")
        st.exception(e)  # Show full traceback for debugging
        return None
    finally:
        conn.close()

def get_trial_data_count():
    """Get count of data collected for this trial from trial_temp table"""
    # ... keep existing code
    conn = get_db_connection()
    if not conn:
        return 0
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM trial_temp 
                WHERE trial_id = %s
            """, (trial_id,))
            count = cursor.fetchone()[0]
            return count
            
    except Exception as e:
        st.error(f"Error counting trial data: {str(e)}")
        return 0
    finally:
        conn.close()

def end_trial():
    """End trial and save data in a simplified time-series format"""
    # ... keep existing code
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        with conn.cursor() as cursor:
            # Get all data from trial_temp
            cursor.execute("""
                SELECT sensor_data, timestamp 
                FROM trial_temp 
                WHERE trial_id = %s 
                ORDER BY timestamp ASC
            """, (trial_id,))
            rows = cursor.fetchall()
            
            if not rows:
                st.warning("No data collected for this trial!")
                return False
            
            # Create a simple time-series format with arrays for each parameter
            simple_data = {
                "timestamps": []
            }
            
            # First pass: collect all possible keys and timestamps
            all_keys = set()
            for row in rows:
                sensor_data, timestamp = row
                
                # Handle timestamp
                if isinstance(timestamp, datetime):
                    simple_data["timestamps"].append(timestamp.isoformat())
                else:
                    simple_data["timestamps"].append(str(timestamp))
                
                # Parse sensor_data if it's a string
                if isinstance(sensor_data, str):
                    try:
                        sensor_data = json.loads(sensor_data)
                    except:
                        # Skip invalid JSON
                        continue
                
                # Collect all keys
                if isinstance(sensor_data, dict):
                    for key in sensor_data.keys():
                        # Skip problematic keys
                        if key in ["Rows", "Index", "__index_level_0__"]:
                            continue
                        all_keys.add(key)
            
            # Initialize arrays for each parameter
            for key in all_keys:
                simple_data[key] = []
            
            # Second pass: fill in the data arrays
            for row in rows:
                sensor_data, timestamp = row
                
                # Parse sensor_data if it's a string
                if isinstance(sensor_data, str):
                    try:
                        sensor_data = json.loads(sensor_data)
                    except:
                        # For invalid JSON, add null values for all parameters
                        for key in all_keys:
                            simple_data[key].append(None)
                        continue
                
                # Add values for each parameter
                if isinstance(sensor_data, dict):
                    for key in all_keys:
                        if key in sensor_data:
                            value = sensor_data[key]
                            # Convert to appropriate type
                            try:
                                if isinstance(value, (int, float)):
                                    simple_data[key].append(float(value))
                                elif isinstance(value, str) and value.replace('.', '', 1).isdigit():
                                    simple_data[key].append(float(value))
                                elif isinstance(value, bool):
                                    simple_data[key].append(bool(value))
                                elif value is None:
                                    simple_data[key].append(None)
                                else:
                                    simple_data[key].append(str(value))
                            except:
                                simple_data[key].append(None)
                        else:
                            # Parameter not present in this reading
                            simple_data[key].append(None)
            
            # Insert into patient_data using the custom encoder for datetime objects
            # Use json.dumps directly to avoid double-escaping
            json_data = json.dumps(simple_data, cls=DateTimeEncoder)
            
            # Create metadata for the file_data column
            # This provides useful context about the trial data
            start_time = simple_data["timestamps"][0] if simple_data["timestamps"] else "unknown"
            end_time = simple_data["timestamps"][-1] if simple_data["timestamps"] else "unknown"
            
            # Calculate some basic statistics if possible
            stats = {}
            for key in simple_data:
                if key != "timestamps":
                    values = [v for v in simple_data[key] if v is not None]
                    if values:
                        stats[key] = {
                            "min": min(values),
                            "max": max(values),
                            "avg": sum(values) / len(values)
                        }
            
            # Format the metadata as a readable string
            metadata = (
                f"Trial {trial_id} for patient {patient_id}\n"
                f"Data points: {len(simple_data['timestamps'])}\n"
                f"Parameters: {', '.join(key for key in simple_data.keys() if key != 'timestamps')}\n"
                f"Time range: {start_time} to {end_time}\n"
                f"Recorded on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Statistics:\n"
            )
            
            # Add statistics for each parameter
            for key, stat in stats.items():
                metadata += f"  {key}: min={stat['min']:.2f}, max={stat['max']:.2f}, avg={stat['avg']:.2f}\n"
            
            # Convert metadata to binary for storage in BYTEA column
            binary_metadata = metadata.encode('utf-8')
            
            # Insert with both JSON data and binary metadata
            cursor.execute("""
                INSERT INTO patient_data (patient_id, data, file_data)
                VALUES (%s, %s::json, %s)
            """, (patient_id, json_data, binary_metadata))
            
            # Update trial end time
            cursor.execute("""
                UPDATE patient_trials 
                SET end_time = NOW()
                WHERE trial_id = %s
            """, (trial_id,))
            
            # Clean up temp data
            cursor.execute("DELETE FROM trial_temp WHERE trial_id = %s", (trial_id,))
            
            conn.commit()
            
            # Clear session
            if "current_trial_id" in st.session_state:
                del st.session_state.current_trial_id
            
            return True
            
    except Exception as e:
        st.error(f"Error ending trial: {str(e)}")
        st.exception(e)  # This will show the full traceback for debugging
        conn.rollback()  # Rollback the transaction on error
        return False
    finally:
        conn.close()

# Layout for trial information and controls
col1, col2 = st.columns([1, 3])

with col1:
    st.markdown("""
    <div class="card">
        <h3>Trial Information</h3>
    """, unsafe_allow_html=True)
    
    # Update trial data count in sidebar
    data_count = get_trial_data_count()
    st.markdown(f"""
        <div class="status-active">Active Trial: #{trial_id}</div>
        <div class="progress-indicator">
            <div class="bar" style="width: {min(100, data_count/5)}%"></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.metric("Data Points Collected", data_count)
    
    # Ensure trial_start_time resets when trial_id changes
    if "previous_trial_id" not in st.session_state or st.session_state["previous_trial_id"] != trial_id:
        st.session_state["trial_start_time"] = datetime.now()
        st.session_state["previous_trial_id"] = trial_id
    
    # Calculate trial duration
    current_time = datetime.now()
    start_time = st.session_state["trial_start_time"]
    duration = current_time - start_time
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    duration_str = f"{hours}h {minutes}m {seconds}s"
    st.metric("Trial Duration", duration_str)
    
    # End trial button
    if st.button("🔴 End Trial", type="primary", use_container_width=True):
        with st.spinner("Saving trial data..."):
            if end_trial():
                st.success("Trial completed and data saved successfully!")
                time.sleep(1)  # Small delay for better UX
                st.switch_page("pages/patient_dashboard.py")
            else:
                st.error("Failed to end trial. Please try again or contact support.")
    
    st.markdown("</div>", unsafe_allow_html=True)  # Close the card div

# Get current data for visualization
with col2:
    st.markdown("""
    <div class="card live-data">
        <h3>Live Sensor Data</h3>
        <p>Data refreshes every 7 seconds. All data is being saved automatically.</p>
    </div>
    """, unsafe_allow_html=True)
    
    df = get_live_data()
    
    if df is not None and not df.empty:
        try:
            # Get numerical columns
            param_columns = [col for col in df.columns if col != 'timestamp' and pd.api.types.is_numeric_dtype(df[col])]
            
            if not param_columns:
                st.warning("No numerical data found in the sensor readings.")
            else:
                # Create line plots
                for param in param_columns:
                    try:
                        # Create a clean copy of the data for plotting
                        plot_df = pd.DataFrame({
                            'timestamp': df['timestamp'],
                            param: df[param].astype(float)  # Ensure numeric type
                        })
                        
                        # Remove NaN values
                        plot_df = plot_df.dropna()
                        
                        if len(plot_df) == 0:
                            st.info(f"No valid data for {param}")
                            continue
                        
                        fig = px.line(
                            plot_df,
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
                            yaxis=dict(showgrid=True),
                            plot_bgcolor='rgba(255,255,255,0.8)',
                            paper_bgcolor='rgba(255,255,255,0)',
                            font=dict(color='#2c3e50')
                        )
                        
                        # Add rolling average if we have enough data points
                        if len(plot_df) >= 5:
                            # Calculate rolling average
                            rolling_avg = plot_df[param].rolling(window=min(5, len(plot_df))).mean()
                            
                            fig.add_scatter(
                                x=plot_df['timestamp'],
                                y=rolling_avg,
                                name=f"{param} (5s avg)",
                                line=dict(color='#e74c3c', width=2, dash='dot')
                            )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Add metrics for this parameter
                        current_val = plot_df[param].iloc[-1] if len(plot_df) > 0 else "N/A"
                        avg_val = plot_df[param].mean() if len(plot_df) > 0 else "N/A"
                        min_val = plot_df[param].min() if len(plot_df) > 0 else "N/A"
                        max_val = plot_df[param].max() if len(plot_df) > 0 else "N/A"
                        
                        metrics_cols = st.columns(4)
                        metrics_cols[0].metric("Current", f"{current_val:.1f}" if isinstance(current_val, (int, float)) else current_val)
                        metrics_cols[1].metric("Average", f"{avg_val:.1f}" if isinstance(avg_val, (int, float)) else avg_val)
                        metrics_cols[2].metric("Min", f"{min_val:.1f}" if isinstance(min_val, (int, float)) else min_val)
                        metrics_cols[3].metric("Max", f"{max_val:.1f}" if isinstance(max_val, (int, float)) else max_val)
                    except Exception as e:
                        st.error(f"Error plotting {param}: {str(e)}")
        except Exception as e:
            st.error(f"Error processing data for visualization: {str(e)}")
            st.exception(e)  # Show full traceback for debugging
    else:
        st.info("Waiting for sensor readings...")
        
        # Add a placeholder with animated dots
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <div style="display: inline-block; margin-bottom: 1rem;">
                <div class="loader"></div>
            </div>
            <p style="color: #7f8c8d; font-style: italic;">Waiting for data to stream from your sensors...</p>
        </div>
        <style>
        .loader {
            border: 5px solid #f3f3f3;
            border-radius: 50%;
            border-top: 5px solid #3498db;
            width: 50px;
            height: 50px;
            animation: spin 2s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        </style>
        """, unsafe_allow_html=True)

# Debug section in expander
with st.expander("Technical Information", expanded=False):
    st.subheader("Data Format Preview")
    if df is not None and not df.empty:
        # Create a preview of the simplified time-series format
        preview_data = {
            "timestamps": df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%f').tolist()[:5]
        }
        
        for param in [col for col in df.columns if col != 'timestamp']:
            preview_data[param] = df[param].tolist()[:5]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**JSON Data Format**")
            st.json(preview_data)
        
        with col2:
            st.markdown("**Storage Information**")
            st.markdown(f"""
            - **Trial ID:** {trial_id}
            - **Patient ID:** {patient_id}
            - **Data Points:** {data_count}
            - **Storage Database:** PostgreSQL
            - **Auto-save Interval:** Continuous
            """)
        
        # Also show metadata preview
        st.subheader("Metadata Preview")
        
        # Calculate some basic statistics for the preview
        stats = {}
        for key in preview_data:
            if key != "timestamps":
                values = [v for v in preview_data[key] if v is not None]
                if values:
                    try:
                        stats[key] = {
                            "min": min(values),
                            "max": max(values),
                            "avg": sum(values) / len(values)
                        }
                    except:
                        pass
        
        # Format the metadata preview
        metadata_preview = (
            f"Trial {trial_id} for patient {patient_id}\n"
            f"Data points: {len(preview_data['timestamps'])} (preview only)\n"
            f"Parameters: {', '.join(key for key in preview_data.keys() if key != 'timestamps')}\n"
            f"Recorded on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Statistics (preview only):\n"
        )
        
        # Add statistics for each parameter
        for key, stat in stats.items():
            metadata_preview += f"  {key}: min={stat['min']:.2f}, max={stat['max']:.2f}, avg={stat['avg']:.2f}\n"
        
        st.code(metadata_preview)

# Navigation footer
st.markdown("""
<div style="margin-top: 2rem; display: flex; justify-content: center;">
""", unsafe_allow_html=True)

if st.button("← Return to Dashboard", use_container_width=True):
    st.switch_page("pages/patient_dashboard.py")

st.markdown("</div>", unsafe_allow_html=True)  # Close the flex container
