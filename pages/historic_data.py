
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime, timedelta
from backend_auth import get_db_connection
from backend_patient_dashboard import *

# Page configuration with wider layout
st.set_page_config(page_title="Patient Data Comparison", layout="wide")

# Apply custom CSS
with open("frontend/static/enhanced_style.css", "r") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Add background patterns
st.markdown("""
<div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: -1; opacity: 0.03; pointer-events: none;">
    <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
        <pattern id="pattern" width="40" height="40" patternUnits="userSpaceOnUse">
            <circle cx="20" cy="20" r="2" fill="#3498db" />
        </pattern>
        <rect width="100%" height="100%" fill="url(#pattern)" />
    </svg>
</div>
""", unsafe_allow_html=True)

# Dashboard header
st.markdown("""
<div style="text-align: center; margin-bottom: 1.5rem;">
    <h1>🔍 Historical Data Analysis</h1>
    <p style="color: #7f8c8d; margin-top: -2rem;">Compare and analyze your past monitoring sessions</p>
</div>
""", unsafe_allow_html=True)

# **Ensure User is Logged In**
if "patient_id" not in st.session_state:
    st.error("Please log in first!")
    st.stop()

patient_id = st.session_state["patient_id"]
username = st.session_state["username"]

# Display patient info
with st.container():
    st.markdown("""
    <div class="card">
        <h3>Patient Information</h3>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Patient ID", value=patient_id)
    with col2:
        st.metric(label="Username", value=username)
        
    st.markdown("</div>", unsafe_allow_html=True)  # Close the card div

# Helper functions (keeping existing functions)
def get_data_instance(data_id: str):
    # ... keep existing code
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pd.*, p.username, pc.comment
        FROM patient_data pd
        JOIN patients p ON pd.patient_id = p.patient_id
        LEFT JOIN patient_comments pc ON pd.data_id = pc.data_id
        WHERE pd.data_id = %s
    """, (data_id,))
    
    data = cursor.fetchone()
    cursor.close()
    conn.close()
    return data

def get_patient_data_ids(patient_id):
    # ... keep existing code
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT data_id, created_at 
        FROM patient_data 
        WHERE patient_id = %s
        ORDER BY created_at DESC
    """, (patient_id,))
    data_ids = cursor.fetchall()
    cursor.close()
    conn.close()
    return data_ids

def load_data(data_id):
    # ... keep existing code
    raw_data = get_data_instance(data_id)
    
    if not raw_data:
        return None
    
    # Convert tuple to dictionary with column names
    column_names = ["data_id", "patient_id", "data", "created_at", "file_data", "username", "comment"]
    data_dict = {}
    
    # Check if raw_data is a tuple or list (database row)
    if isinstance(raw_data, (tuple, list)):
        # Map values to column names
        for i, col in enumerate(column_names):
            if i < len(raw_data):
                data_dict[col] = raw_data[i]
    elif isinstance(raw_data, dict):
        # If it's already a dictionary, use it directly
        data_dict = raw_data
    else:
        st.error(f"Unexpected data format for {data_id}: {type(raw_data)}")
        return None
    
    # Process the JSON data
    json_data = data_dict.get("data", "{}")
    
    # If it's a string, try to parse it as JSON
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except json.JSONDecodeError:
            st.warning(f"Failed to parse JSON data for data_id {data_id}")
            return None
    
    # Try to convert to DataFrame
    try:
        # If it's a list of records
        if isinstance(json_data, list):
            df = pd.DataFrame(json_data)
        # If it's a dict with arrays
        elif isinstance(json_data, dict):
            # Check if all values are lists of the same length
            if all(isinstance(v, list) for v in json_data.values()) and len(set(len(v) for v in json_data.values() if isinstance(v, list))) <= 1:
                df = pd.DataFrame(json_data)
            else:
                # Handle nested dictionaries by flattening
                df = pd.DataFrame([json_data])
        else:
            st.warning(f"Unexpected JSON structure for data_id {data_id}")
            return None
        
        # Add metadata columns
        df['data_id'] = data_id
        df['patient_id'] = data_dict.get('patient_id')
        df['username'] = data_dict.get('username')
        df['created_at'] = data_dict.get('created_at')
        
        # Handle comment - use "N/A" if comment is None or not present
        comment = data_dict.get("comment")
        df['comments'] = "N/A" if comment is None else comment
        
        # Process timestamps if they exist
        if 'timestamps' in df.columns:
            # Convert string timestamps to datetime objects
            try:
                df['timestamps'] = pd.to_datetime(df['timestamps'])
                
                # Add a normalized time column (seconds from start)
                if len(df) > 0:
                    start_time = df['timestamps'].min()
                    df['time_seconds'] = (df['timestamps'] - start_time).dt.total_seconds()
                    
                    # Also add a minutes column for easier reading
                    df['time_minutes'] = df['time_seconds'] / 60
            except Exception as e:
                st.warning(f"Could not process timestamps for data_id {data_id}: {str(e)}")
        
        return df
    except Exception as e:
        st.warning(f"Could not convert data for {data_id} to DataFrame: {str(e)}")
        return None

def get_data_info(data_id, created_at):
    # ... keep existing code
    df = load_data(data_id)

    # Ensure df is valid before accessing its columns
    if df is None or df.empty:
        return {
            "Data ID": data_id,
            "Timestamp": format_timestamp(created_at),
            "Rows": "N/A",
            "Parameters": "N/A",
            "Example Parameters": "N/A",
            "Comments": "N/A"
        }
    
    # Extract a single comment (assuming each data_id has only one)
    comments = "N/A"
    if "comments" in df.columns:
        # Get the first non-null comment, or "N/A" if all are null
        non_null_comments = df["comments"].dropna()
        if not non_null_comments.empty and non_null_comments.iloc[0] != "N/A":
            comments = non_null_comments.iloc[0]

    # Get number of rows
    row_count = len(df)
    
    # Get numeric columns (parameters)
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    numeric_cols = [col for col in numeric_cols if col not in ['data_id', 'patient_id', 'time_seconds', 'time_minutes']]
    param_count = len(numeric_cols)
    param_examples = ", ".join(numeric_cols[:3])
    if len(numeric_cols) > 3:
        param_examples += "..."
    
    # Get duration if time_seconds exists
    duration = "N/A"
    if 'time_seconds' in df.columns and not df['time_seconds'].empty:
        max_seconds = df['time_seconds'].max()
        if max_seconds < 60:
            duration = f"{max_seconds:.1f} seconds"
        elif max_seconds < 3600:
            duration = f"{max_seconds/60:.1f} minutes"
        else:
            duration = f"{max_seconds/3600:.1f} hours"
    
    return {
        "Data ID": data_id,
        "Timestamp": format_timestamp(created_at),
        "Rows": row_count,
        "Parameters": param_count,
        "Duration": duration,
        "Example Parameters": param_examples,
        "Comments": comments
    }

def format_timestamp(created_at):
    # ... keep existing code
    if isinstance(created_at, datetime):
        return created_at.strftime("%d-%m-%Y %H:%M")
    
    try:
        return datetime.fromisoformat(str(created_at).replace('Z', '+00:00')).strftime("%d-%m-%Y %H:%M")
    except Exception:
        return str(created_at)

# Main content
st.markdown("""
<div class="card">
    <h3>Data Selection</h3>
    <p>Choose data sets to compare and analyze</p>
""", unsafe_allow_html=True)

# Get data IDs for the patient
all_data_ids = {}
data_ids = get_patient_data_ids(patient_id)

if not data_ids:
    st.warning("No historical data found for your account")
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem; opacity: 0.7;">
        <svg width="80" height="80" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M19 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3ZM19 19H5V5H19V19Z" fill="#7f8c8d"/>
            <path d="M7 12H9V17H7V12Z" fill="#7f8c8d"/>
            <path d="M11 7H13V17H11V7Z" fill="#7f8c8d"/>
            <path d="M15 9H17V17H15V9Z" fill="#7f8c8d"/>
        </svg>
        <p style="margin-top: 1rem;">Begin a new trial to collect data for future comparison</p>
        <button onclick="window.location.href='patient_dashboard'" style="padding: 0.5rem 1rem; background-color: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; margin-top: 1rem;">Go to Dashboard</button>
    </div>
    """, unsafe_allow_html=True)
    
    st.stop()

# Collect data info for the table
data_info_list = []
for d_id, created_at in data_ids:
    data_info = get_data_info(d_id, created_at)
    data_info_list.append(data_info)
    
    # Format data IDs for the multiselect
    all_data_ids[d_id] = {
        'display': f"Data ID: {d_id} (Created: {data_info['Timestamp']})",
        'created_at': data_info['Timestamp']
    }

# Display data info table
st.markdown("<p>Available data sets:</p>", unsafe_allow_html=True)
data_info_df = pd.DataFrame(data_info_list)
st.dataframe(data_info_df, use_container_width=True)

# Initialize session state for selected data IDs if not exists
if 'selected_data_ids' not in st.session_state or not set(st.session_state.selected_data_ids).issubset(set(all_data_ids.keys())):
    # Default to selecting the first two data IDs if available
    default_selection = list(all_data_ids.keys())[:min(2, len(all_data_ids))]
    st.session_state.selected_data_ids = default_selection

# Data ID selection
selected_data_ids = st.multiselect(
    "Select Data IDs to Compare",
    options=list(all_data_ids.keys()),
    format_func=lambda x: all_data_ids[x]['display'],
    default=st.session_state.selected_data_ids
)

st.markdown("</div>", unsafe_allow_html=True)  # Close the card div

# Update session state
st.session_state.selected_data_ids = selected_data_ids

if not selected_data_ids:
    st.warning("Please select at least one data ID to analyze")
    st.stop()

# Data ID overlay option (only show if multiple data IDs selected)
with st.container():
    st.markdown("""
    <div class="card">
        <h3>Analysis Settings</h3>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    overlay_data_ids = True
    with col1:
        if len(selected_data_ids) > 1:
            overlay_data_ids = st.checkbox("Overlay data in visualizations", value=True, 
                                          help="If checked, data from all selected data IDs will be shown in the same plots")
    
    # Time normalization option
    with col2:
        use_normalized_time = st.checkbox("Use normalized time (seconds from start)", value=True,
                                        help="If checked, time will be shown as seconds from the start of each trial")
    
    st.markdown("</div>", unsafe_allow_html=True)  # Close the card div

# Load data for selected data IDs
data_frames = {}
all_numeric_cols = set()
data_id_numeric_cols = {}  # Track numeric columns per data ID
common_numeric_cols = None
timestamp_cols = set()

with st.spinner("Loading data..."):
    for data_id in selected_data_ids:
        df = load_data(data_id)
        if df is not None:
            data_frames[data_id] = df
            
            # Collect numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            numeric_cols = [col for col in numeric_cols if col not in ['data_id', 'patient_id', 'time_seconds', 'time_minutes']]
            all_numeric_cols.update(numeric_cols)
            data_id_numeric_cols[data_id] = numeric_cols
            
            # Track common numeric columns across all datasets
            if common_numeric_cols is None:
                common_numeric_cols = set(numeric_cols)
            else:
                common_numeric_cols.intersection_update(numeric_cols)
            
            # Try to identify timestamp columns
            time_cols = [col for col in df.columns if any(time_keyword in col.lower() for time_keyword in 
                        ['time', 'date', 'timestamp', 'second', 'minute', 'hour', 'day'])]
            timestamp_cols.update(time_cols)

if not data_frames:
    st.error("Could not load any data for the selected data IDs")
    st.stop()

# Convert sets to lists for UI
all_numeric_cols = list(all_numeric_cols)
common_numeric_cols = list(common_numeric_cols) if common_numeric_cols else []
timestamp_cols = list(timestamp_cols)

# Display data summary
with st.container():
    st.markdown("""
    <div class="card">
        <h3>Data Summary</h3>
    """, unsafe_allow_html=True)
    
    # Create a tabular summary
    summary_data = []
    for data_id, df in data_frames.items():
        # Format the timestamp
        timestamp = "Unknown"
        if 'created_at' in df.columns and not df.empty:
            created_at = df['created_at'].iloc[0]
            if isinstance(created_at, datetime):
                timestamp = created_at.strftime("%d-%m-%Y %H:%M")
            elif isinstance(created_at, str):
                # Try to parse the string timestamp
                try:
                    # Try different formats
                    try:
                        dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S.%f")
                    except ValueError:
                        try:
                            dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            try:
                                dt = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%f")
                            except ValueError:
                                try:
                                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                except ValueError:
                                    # If all parsing attempts fail, use the string as is
                                    timestamp = created_at
                                    dt = None
                    
                    if dt:
                        timestamp = dt.strftime("%d-%m-%Y %H:%M")
                except Exception:
                    # If parsing fails, use the string as is
                    timestamp = created_at
        
        # Get duration if available
        duration = "N/A"
        if 'time_seconds' in df.columns and not df.empty:
            max_seconds = df['time_seconds'].max()
            if max_seconds < 60:
                duration = f"{max_seconds:.1f} seconds"
            elif max_seconds < 3600:
                duration = f"{max_seconds/60:.1f} minutes"
            else:
                duration = f"{max_seconds/3600:.1f} hours"
        
        summary_data.append({
            'Data ID': data_id,
            'Timestamp': timestamp,
            'Rows': len(df),
            'Duration': duration,
            'Columns': len(df.columns),
            'Numeric Columns': len(data_id_numeric_cols.get(data_id, []))
        })
    
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True)
    
    st.markdown("</div>", unsafe_allow_html=True)  # Close the card div

# Show data previews in expandable sections
with st.expander("Preview Data"):
    for data_id, df in data_frames.items():
        st.subheader(f"Data ID: {data_id}")
        # Create a preview DataFrame with the most relevant columns
        preview_cols = []
        
        # Add time columns first if they exist
        if use_normalized_time and 'time_seconds' in df.columns:
            preview_cols.append('time_seconds')
        elif 'timestamps' in df.columns:
            preview_cols.append('timestamps')
        
        # Add numeric columns
        numeric_cols = data_id_numeric_cols.get(data_id, [])
        preview_cols.extend(numeric_cols[:5])  # Limit to first 5 numeric columns
        
        # Create the preview DataFrame
        if preview_cols:
            preview_df = df[preview_cols].copy()
            st.dataframe(preview_df, use_container_width=True)
        else:
            st.dataframe(df.drop(columns=["data_id", "patient_id", "username", "comments"], errors="ignore"), use_container_width=True)

# Parameter selection
with st.container():
    st.markdown("""
    <div class="card">
        <h3>Parameter Selection</h3>
    """, unsafe_allow_html=True)
    
    # Option to use common parameters only
    use_common_only = st.checkbox("Show only parameters common to all datasets", value=True if common_numeric_cols else False)
    
    if use_common_only and common_numeric_cols:
        available_params = common_numeric_cols
    else:
        available_params = all_numeric_cols
    
    # Select parameters to visualize
    selected_params = st.multiselect(
        "Select parameters to compare",
        options=available_params,
        default=available_params[:min(3, len(available_params))]
    )
    
    st.markdown("</div>", unsafe_allow_html=True)  # Close the card div

if not selected_params:
    st.warning("Please select at least one parameter to visualize")
    st.stop()

# Visualization options
with st.container():
    st.markdown("""
    <div class="card">
        <h3>Visualization</h3>
    """, unsafe_allow_html=True)
    
    # Choose visualization type
    viz_type = st.radio(
        "Select visualization type",
        options=["Line Charts", "Box Plots", "Violin Plots", "Bar Charts", "Scatter Matrix", "Heatmap"],
        horizontal=True
    )
    
    st.markdown("</div>", unsafe_allow_html=True)  # Close the card div

# Create visualizations based on selected type
with st.container():
    if viz_type == "Line Charts":
        # One chart per parameter
        for param in selected_params:
            fig = go.Figure()
            
            for data_id, df in data_frames.items():
                if param in df.columns:
                    # Determine x-axis values based on user preference
                    if use_normalized_time and 'time_seconds' in df.columns:
                        x_values = df['time_seconds']
                        x_title = "Time (seconds from start)"
                    elif 'timestamps' in df.columns:
                        x_values = df['timestamps']
                        x_title = "Timestamp"
                    else:
                        x_values = df.index
                        x_title = "Data Point"
                    
                    fig.add_trace(go.Scatter(
                        x=x_values,
                        y=df[param],
                        mode='lines+markers',
                        name=f"Data ID: {data_id}",
                        line=dict(width=2),
                        marker=dict(size=5)
                    ))
            
            fig.update_layout(
                title=f"{param} Comparison",
                xaxis_title=x_title,
                yaxis_title=param,
                legend_title="Data ID",
                height=400,
                template="plotly_white",
                margin=dict(l=10, r=10, t=40, b=10),
                legend=dict(
                    yanchor="top", 
                    y=0.99, 
                    xanchor="right", 
                    x=0.99,
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="rgba(0,0,0,0.1)",
                    borderwidth=1
                )
            )
            st.plotly_chart(fig, use_container_width=True)
    elif viz_type == "Box Plots":
        # Create a combined dataframe for box plots
        combined_data = []
        
        for param in selected_params:
            for data_id, df in data_frames.items():
                if param in df.columns:
                    param_data = df[param].dropna()
                    temp_df = pd.DataFrame({
                        'Parameter': [param] * len(param_data),
                        'Value': param_data,
                        'Data ID': [f"Data ID: {data_id}"] * len(param_data)
                    })
                    combined_data.append(temp_df)
        
        if combined_data:
            combined_df = pd.concat(combined_data, ignore_index=True)
            
            fig = px.box(
                combined_df, 
                x='Parameter', 
                y='Value', 
                color='Data ID',
                title="Parameter Distribution Comparison",
                points="all"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No valid data for box plots")

    elif viz_type == "Violin Plots":
        # Create a combined dataframe for violin plots
        combined_data = []
        
        for param in selected_params:
            for data_id, df in data_frames.items():
                if param in df.columns:
                    param_data = df[param].dropna()
                    temp_df = pd.DataFrame({
                        'Parameter': [param] * len(param_data),
                        'Value': param_data,
                        'Data ID': [f"Data ID: {data_id}"] * len(param_data)
                    })
                    combined_data.append(temp_df)
        
        if combined_data:
            combined_df = pd.concat(combined_data, ignore_index=True)
            
            fig = px.violin(
                combined_df, 
                x='Parameter', 
                y='Value', 
                color='Data ID',
                box=True,
                title="Parameter Distribution Comparison"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No valid data for violin plots")

    elif viz_type == "Bar Charts":
        # Calculate statistics for bar charts
        stats_data = []
        
        for param in selected_params:
            for data_id, df in data_frames.items():
                if param in df.columns:
                    stats = {
                        'Data ID': f"Data ID: {data_id}",
                        'Parameter': param,
                        'Mean': df[param].mean(),
                        'Median': df[param].median(),
                        'Min': df[param].min(),
                        'Max': df[param].max(),
                        'Std Dev': df[param].std()
                    }
                    stats_data.append(stats)
        
        if stats_data:
            stats_df = pd.DataFrame(stats_data)
            
            # Let user choose which statistic to display
            stat_option = st.selectbox(
                "Select statistic to display",
                options=['Mean', 'Median', 'Min', 'Max', 'Std Dev']
            )
            
            fig = px.bar(
                stats_df, 
                x='Parameter', 
                y=stat_option, 
                color='Data ID',
                barmode='group',
                title=f"{stat_option} Comparison"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No valid data for bar charts")

    elif viz_type == "Scatter Matrix":
        # Only use the first few parameters to avoid overcrowding
        display_params = selected_params[:min(4, len(selected_params))]
        
        if len(display_params) < 2:
            st.warning("Please select at least 2 parameters for scatter matrix")
        else:
            # Create a combined dataframe with an identifier column
            combined_data = []
            
            for data_id, df in data_frames.items():
                # Check if all selected parameters exist in this dataframe
                if all(param in df.columns for param in display_params):
                    temp_df = df[display_params].copy()
                    temp_df['Data ID'] = f"Data ID: {data_id}"
                    combined_data.append(temp_df)
            
            if combined_data:
                combined_df = pd.concat(combined_data, ignore_index=True)
                
                fig = px.scatter_matrix(
                    combined_df,
                    dimensions=display_params,
                    color='Data ID',
                    title="Parameter Relationships"
                )
                fig.update_layout(height=800)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No data frames contain all the selected parameters for scatter matrix")

    elif viz_type == "Heatmap":
        # Calculate correlation matrices for each dataset
        for data_id, df in data_frames.items():
            # Filter to only include selected parameters that exist in this dataframe
            valid_params = [param for param in selected_params if param in df.columns]
            
            if len(valid_params) >= 2:
                st.subheader(f"Correlation Heatmap - Data ID: {data_id}")
                
                # Calculate correlation matrix
                corr_matrix = df[valid_params].corr()
                
                # Create heatmap
                fig = px.imshow(
                    corr_matrix,
                    text_auto=True,
                    color_continuous_scale='RdBu_r',
                    title=f"Correlation Matrix - Data ID: {data_id}"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"Not enough valid parameters for correlation heatmap in Data ID: {data_id}")

# Time-series analysis (if normalized time is available)
if use_normalized_time and any('time_seconds' in df.columns for df in data_frames.values()):
    with st.expander("Time-Series Analysis"):
        st.subheader("Parameter Trends Over Time")
        
        # Select a parameter for detailed time analysis
        if selected_params:
            time_param = st.selectbox("Select parameter for time analysis", options=selected_params)
            
            # Create a combined plot with normalized time
            fig = go.Figure()
            
            for data_id, df in data_frames.items():
                if time_param in df.columns and 'time_seconds' in df.columns:
                    # Add the raw data
                    fig.add_trace(go.Scatter(
                        x=df['time_seconds'],
                        y=df[time_param],
                        mode='lines',
                        name=f"Data ID: {data_id} (raw)",
                        line=dict(width=1)
                    ))
                    
                    # Add a smoothed version if enough data points
                    if len(df) > 5:
                        # Create a smoothed version using rolling average
                        window_size = max(5, len(df) // 20)  # Use 5% of data points or at least 5
                        smoothed = df[time_param].rolling(window=window_size, center=True).mean()
                        
                        fig.add_trace(go.Scatter(
                            x=df['time_seconds'],
                            y=smoothed,
                            mode='lines',
                            name=f"Data ID: {data_id} (smoothed)",
                            line=dict(width=3)
                        ))
            
            fig.update_layout(
                title=f"{time_param} Over Time",
                xaxis_title="Time (seconds from start)",
                yaxis_title=time_param,
                legend_title="Data Source",
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Add rate of change analysis
            st.subheader("Rate of Change Analysis")
            
            rate_fig = go.Figure()
            
            for data_id, df in data_frames.items():
                if time_param in df.columns and 'time_seconds' in df.columns and len(df) > 5:
                    # Calculate rate of change (derivative)
                    df = df.sort_values('time_seconds')
                    df['rate'] = df[time_param].diff() / df['time_seconds'].diff()
                    
                    # Smooth the rate of change
                    window_size = max(5, len(df) // 20)
                    smoothed_rate = df['rate'].rolling(window=window_size, center=True).mean()
                    
                    rate_fig.add_trace(go.Scatter(
                        x=df['time_seconds'],
                        y=smoothed_rate,
                        mode='lines',
                        name=f"Data ID: {data_id}"
                    ))
            
            rate_fig.update_layout(
                title=f"Rate of Change for {time_param}",
                xaxis_title="Time (seconds from start)",
                yaxis_title=f"Rate of Change ({time_param}/second)",
                legend_title="Data Source",
                template="plotly_white"
            )
            st.plotly_chart(rate_fig, use_container_width=True)

# Statistical comparison
with st.expander("Statistical Comparison"):
    st.subheader("Parameter Statistics")
    
    # Create a table of statistics for each parameter and dataset
    stats_data = []
    
    for param in selected_params:
        for data_id, df in data_frames.items():
            if param in df.columns:
                stats = {
                    'Parameter': param,
                    'Data ID': data_id,
                    'Count': df[param].count(),
                    'Mean': df[param].mean(),
                    'Median': df[param].median(),
                    'Std Dev': df[param].std(),
                    'Min': df[param].min(),
                    'Max': df[param].max(),
                    'Range': df[param].max() - df[param].min(),
                    '25%': df[param].quantile(0.25),
                    '75%': df[param].quantile(0.75),
                    'IQR': df[param].quantile(0.75) - df[param].quantile(0.25)
                }
                stats_data.append(stats)
    
    if stats_data:
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df)
    else:
        st.warning("No valid data for statistical comparison")

# Navigation
st.markdown("""
<div style="display: flex; justify-content: center; margin-top: 2rem;">
""", unsafe_allow_html=True)

if st.button("← Back to Dashboard", use_container_width=True):
    st.switch_page("pages/patient_dashboard.py")

st.markdown("</div>", unsafe_allow_html=True)
