import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import json
from backend_auth import get_db_connection

st.set_page_config(page_title="Trial Recording", layout="wide")

# Ensure user is logged in
if "patient_id" not in st.session_state:
    st.error("Please log in first!")
    st.stop()

patient_id = st.session_state["patient_id"]
trial_id = st.session_state.get("current_trial_id")

if not trial_id:
    st.error("No active trial! Please start a trial from the dashboard.")
    st.stop()

st.title("📝 Trial Recording")
st.subheader(f"Trial #{trial_id}")

# Auto-refresh for live data
st_autorefresh(interval=7000, key="trial_refresh")

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def get_live_data():
    """Get the most recent data from live_patient_data table"""
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

# Get current data for visualization
df = get_live_data()

# Update trial data count in sidebar
data_count = get_trial_data_count()
st.sidebar.subheader("Trial Information")
st.sidebar.info(f"Trial #{trial_id} is active")
st.sidebar.metric("Data Points Collected", data_count)

# Display data
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
                        yaxis=dict(showgrid=True)
                    )
                    
                    # Add rolling average if we have enough data points
                    if len(plot_df) >= 5:
                        # Calculate rolling average
                        rolling_avg = plot_df[param].rolling(window=min(5, len(plot_df))).mean()
                        
                        fig.add_scatter(
                            x=plot_df['timestamp'],
                            y=rolling_avg,
                            name=f"{param} (5s avg)",
                            line=dict(color='red', width=1, dash='dot')
                        )
                    
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error plotting {param}: {str(e)}")
    except Exception as e:
        st.error(f"Error processing data for visualization: {str(e)}")
        st.exception(e)  # Show full traceback for debugging
else:
    st.info("Waiting for sensor readings...")

# End trial button
if st.button("🔴 End Trial", type="primary"):
    with st.spinner("Saving trial data..."):
        if end_trial():
            st.success("Trial completed and data saved!")
            st.switch_page("pages/patient_dashboard.py")
        else:
            st.error("Failed to end trial. Please try again or contact support.")

# Add a debug section to show the data format
if st.checkbox("Show data format preview"):
    if df is not None and not df.empty:
        # Create a preview of the simplified time-series format
        preview_data = {
            "timestamps": df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%f').tolist()[:5]
        }
        
        for param in [col for col in df.columns if col != 'timestamp']:
            preview_data[param] = df[param].tolist()[:5]
        
        st.subheader("Data Format Preview")
        st.json(preview_data)
        
        # Also show metadata preview
        st.subheader("Metadata Preview (stored in file_data)")
        
        # Calculate some basic statistics for the preview
        stats = {}
        for key in preview_data:
            if key != "timestamps":
                values = [v for v in preview_data[key] if v is not None]
                if values:
                    stats[key] = {
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values)
                    }
        
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
        st.caption("This metadata will be stored in the file_data column when you end the trial.")