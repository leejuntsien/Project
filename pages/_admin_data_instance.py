import streamlit as st
import plotly.express as px
import pandas as pd
import json
from backend_patient_info import get_data_instance
from utils.security import require_admin_auth, is_admin_authenticated
from datetime import datetime

st.set_page_config(page_title="Data Instance View", layout="wide")

# Check authentication
if not is_admin_authenticated():
    st.error("⚠️ Access Denied: Admin authentication required")
    st.warning("Please log in to access data.")
    if st.button("Go to Login"):
        st.switch_page("pages/_admin_auth.py")
    st.stop()

# Get data ID from URL parameter or session state
if st.query_params.get("id") is not None:
    data_id = st.query_params.get("id")
elif "data_id" in st.session_state and st.session_state.data_id:
    data_id = st.session_state.data_id
elif "dialog_data_id" in st.session_state and st.session_state.dialog_data_id:
    data_id = st.session_state.dialog_data_id
else:
    data_id = None

# Display data ID in the title
st.title(f"Data Instance: {data_id}")

if not data_id:
    st.warning("No data ID specified")
    if st.button("← Back"):
        st.switch_page("pages/test_adminPatientData.py")
    st.stop()

# Get data instance from the database
raw_data = get_data_instance(data_id)

if not raw_data:
    st.error("Data not found")
    if st.button("← Back"):
        st.switch_page("pages/test_adminPatientData.py")
    st.stop()

# Convert tuple to dictionary with column names
# Based on the columns you mentioned: data_id, patient_id, data, created_at, file_data
column_names = ["data_id", "patient_id", "data", "created_at", "file_data", "username"]
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
    st.error(f"Unexpected data format: {type(raw_data)}")
    st.write(raw_data)
    if st.button("← Back"):
        st.switch_page("pages/test_adminPatientData.py")
    st.stop()

# Format the created_at datetime to show only date and time up to minutes
if "created_at" in data_dict and data_dict["created_at"]:
    try:
        # If it's already a datetime object
        if isinstance(data_dict["created_at"], datetime):
            formatted_date = data_dict["created_at"].strftime("%Y-%m-%d %H:%M")
        # If it's a string, parse it first
        elif isinstance(data_dict["created_at"], str):
            # Try different formats
            try:
                dt = datetime.strptime(data_dict["created_at"], "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                try:
                    dt = datetime.strptime(data_dict["created_at"], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        dt = datetime.strptime(data_dict["created_at"], "%Y-%m-%dT%H:%M:%S.%f")
                    except ValueError:
                        dt = datetime.fromisoformat(data_dict["created_at"].replace('Z', '+00:00'))
            
            formatted_date = dt.strftime("%Y-%m-%d %H:%M")
        else:
            formatted_date = str(data_dict["created_at"])
        
        # Update the dictionary with the formatted date
        data_dict["created_at"] = formatted_date
    except Exception as e:
        st.warning(f"Could not format date: {e}")
        # Keep the original value if formatting fails

# Display metadata in a prominent way
st.header("Patient Information")
col1, col2, col3 = st.columns(3)
col1.metric("Data ID", data_dict.get("data_id", "N/A"))
col1.metric("Patient ID", data_dict.get("patient_id", "N/A"))
col2.metric("Username", data_dict.get("username", "N/A"))
col2.metric("Created At", data_dict.get("created_at", "N/A"))
col3.metric("File Data Size", f"{len(str(data_dict.get('file_data', ''))) if data_dict.get('file_data') else 0} bytes")

# Process the JSON data
json_data = data_dict.get("data", "{}")

# If it's a string, try to parse it as JSON
if isinstance(json_data, str):
    try:
        json_data = json.loads(json_data)
    except json.JSONDecodeError as e:
        st.error(f"Error parsing JSON data: {str(e)}")
        st.text(json_data)  # Show the raw string if it can't be parsed

# Display the JSON data
st.header("Data Content")
with st.expander("Raw JSON Data", expanded=True):
    st.json(json_data)

# Try to convert to DataFrame if it's a list or dict
if isinstance(json_data, (list, dict)):
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
        
        if not df.empty:
            # Format any datetime columns in the DataFrame
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M")
            
            st.header("Data as Table")
            st.dataframe(df)
            
            # Visualization section
            st.header("Visualizations")
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

            if numeric_cols:
                # Add a toggle for overlay mode
                overlay_mode = st.checkbox("Enable plot overlay mode", help="Select multiple columns to display on the same chart")
                
                if overlay_mode:
                    # Multi-select for overlaying multiple plots
                    selected_columns = st.multiselect(
                        "Select columns to plot (overlay mode)",
                        options=numeric_cols,
                        default=[numeric_cols[0]] if numeric_cols else None
                    )
                    
                    if selected_columns:
                        # Create a line chart with multiple lines
                        fig = px.line(
                            df, 
                            y=selected_columns, 
                            title=f"Overlay Plot of {', '.join(selected_columns)}"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Add a scatter plot option for the first two selected columns
                        if len(selected_columns) >= 2 and st.checkbox("Add scatter plot for first two selected columns"):
                            scatter_fig = px.scatter(
                                df, 
                                x=selected_columns[0], 
                                y=selected_columns[1],
                                title=f"Scatter Plot: {selected_columns[0]} vs {selected_columns[1]}"
                            )
                            st.plotly_chart(scatter_fig, use_container_width=True)
                else:
                    # Single plot selection with radio buttons
                    if len(numeric_cols) >= 1:
                        selected_index = st.radio(
                            "Select a column to plot",
                            options=range(len(numeric_cols)),
                            format_func=lambda i: numeric_cols[i]
                        )
                        
                        # Create a line chart for the selected column
                        fig = px.line(
                            df, 
                            y=numeric_cols[selected_index], 
                            title=f"Line Chart of {numeric_cols[selected_index]}"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Add histogram option
                        if st.checkbox("Show histogram"):
                            hist_fig = px.histogram(
                                df, 
                                x=numeric_cols[selected_index],
                                title=f"Histogram of {numeric_cols[selected_index]}"
                            )
                            st.plotly_chart(hist_fig, use_container_width=True)
                
                # Additional visualization options
                with st.expander("Additional Visualization Options"):
                    if len(numeric_cols) >= 2:
                        st.subheader("Correlation Analysis")
                        
                        # Allow selecting columns for correlation scatter plot
                        x_col = st.selectbox("X-axis", numeric_cols, index=0)
                        y_col = st.selectbox("Y-axis", numeric_cols, index=min(1, len(numeric_cols)-1))
                        
                        if x_col != y_col:
                            # Check if trendline is requested
                            add_trendline = st.checkbox("Add trendline")
                            
                            # Create scatter plot with safe trendline handling
                            try:
                                if add_trendline:
                                    # Try to import statsmodels first to check if it's available
                                    try:
                                        import statsmodels.api
                                        scatter_fig = px.scatter(
                                            df, 
                                            x=x_col, 
                                            y=y_col,
                                            title=f"Scatter Plot: {x_col} vs {y_col}",
                                            trendline="ols"
                                        )
                                    except ImportError:
                                        st.warning("The statsmodels package is required for trendlines but is not installed. Creating plot without trendline.")
                                        scatter_fig = px.scatter(
                                            df, 
                                            x=x_col, 
                                            y=y_col,
                                            title=f"Scatter Plot: {x_col} vs {y_col}"
                                        )
                                else:
                                    scatter_fig = px.scatter(
                                        df, 
                                        x=x_col, 
                                        y=y_col,
                                        title=f"Scatter Plot: {x_col} vs {y_col}"
                                    )
                                st.plotly_chart(scatter_fig, use_container_width=True)
                            except Exception as e:
                                st.error(f"Error creating scatter plot: {str(e)}")
                                st.info("Try selecting different columns or disabling the trendline.")
            else:
                st.info("No numeric columns available for visualization.")

    except Exception as e:
        st.warning(f"Could not convert JSON to DataFrame: {str(e)}")
        st.code(str(json_data))

# Navigation
st.divider()
col1, col2 = st.columns(2)
if col1.button("← Back to Patient Data"):
    st.switch_page("pages/test_adminPatientData.py")
if col2.button("← Back to Patient List"):
    st.switch_page("pages/_admin_patient_info.py")