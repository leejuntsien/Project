
import streamlit as st
import plotly.express as px
import pandas as pd
import json
from backend_patient_info import get_data_instance
from utils.security import require_admin_auth, is_admin_authenticated
from utils.admin_ui import load_admin_css, dashboard_card, create_metric_card, format_button, optimize_streamlit
from datetime import datetime

st.set_page_config(page_title="Data Instance View", layout="wide")

# Load custom CSS
load_admin_css()

# Apply optimizations
optimize_streamlit()

# Check authentication
if not is_admin_authenticated():
    st.error("⚠️ Access Denied: Admin authentication required")
    st.warning("Please log in to access data.")
    format_button("Go to Login", key="login_redirect", on_click=lambda: st.switch_page("pages/_admin_auth.py"))
    st.stop()

# Get data ID from URL parameter or session state
if st.query_params.get("id") is not None:
    data_id = st.query_params.get("id")
    # Store in session state to prevent loss on page refresh
    st.session_state.data_id = data_id
elif "data_id" in st.session_state and st.session_state.data_id:
    data_id = st.session_state.data_id
elif "dialog_data_id" in st.session_state and st.session_state.dialog_data_id:
    data_id = st.session_state.dialog_data_id
    st.session_state.data_id = data_id
else:
    data_id = None

# Display data ID in the title with improved styling
st.markdown(f"""
<div class="admin-header fade-in">
    <h1>Data Instance: {data_id}</h1>
</div>
""", unsafe_allow_html=True)

if not data_id:
    st.warning("No data ID specified")
    format_button("← Back", key="back_btn", type="secondary", 
             on_click=lambda: st.switch_page("pages/test_adminPatientData.py"))
    st.stop()

# Get data instance from the database
raw_data = get_data_instance(data_id)

if not raw_data:
    st.error("Data not found")
    format_button("← Back", key="back_btn", type="secondary", 
             on_click=lambda: st.switch_page("pages/test_adminPatientData.py"))
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
    format_button("← Back", key="back_btn", type="secondary", 
             on_click=lambda: st.switch_page("pages/test_adminPatientData.py"))
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

# Display patient info card with improved styling
st.markdown('<div class="patient-info-card fade-in">', unsafe_allow_html=True)
st.header("Patient Information")
col1, col2, col3 = st.columns(3)
col1.metric("Data ID", data_dict.get("data_id", "N/A"))
col1.metric("Patient ID", data_dict.get("patient_id", "N/A"))
col2.metric("Username", data_dict.get("username", "N/A"))
col2.metric("Created At", data_dict.get("created_at", "N/A"))
col3.metric("File Data Size", f"{len(str(data_dict.get('file_data', ''))) if data_dict.get('file_data') else 0} bytes")
st.markdown('</div>', unsafe_allow_html=True)

# Process the JSON data
json_data = data_dict.get("data", "{}")

# If it's a string, try to parse it as JSON
if isinstance(json_data, str):
    try:
        json_data = json.loads(json_data)
    except json.JSONDecodeError as e:
        st.error(f"Error parsing JSON data: {str(e)}")
        st.text(json_data)  # Show the raw string if it can't be parsed

# Display the JSON data in a nice expandable card
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
            
            # Display data in a nicely styled table
            st.markdown('<div class="data-table-container fade-in">', unsafe_allow_html=True)
            st.header("Data as Table")
            st.dataframe(df, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Visualization section with improved styling
            st.markdown('<div class="visualization-container fade-in">', unsafe_allow_html=True)
            st.header("Visualizations")
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

            if numeric_cols:
                # Create tabs for different visualization options
                viz_tabs = st.tabs(["Line/Bar Charts", "Scatter Plots", "Distribution Analysis", "Correlation Analysis"])
                
                with viz_tabs[0]:  # Line/Bar Charts
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
                            
                            # Add option to switch to bar chart
                            if st.checkbox("Show as bar chart instead"):
                                bar_fig = px.bar(
                                    df, 
                                    y=selected_columns, 
                                    title=f"Bar Chart of {', '.join(selected_columns)}"
                                )
                                st.plotly_chart(bar_fig, use_container_width=True)
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
                
                with viz_tabs[1]:  # Scatter Plots
                    if len(numeric_cols) >= 2:
                        x_col = st.selectbox("X-axis", numeric_cols, index=0, key="scatter_x")
                        y_col = st.selectbox("Y-axis", numeric_cols, index=min(1, len(numeric_cols)-1), key="scatter_y")
                        
                        if x_col != y_col:
                            # Add options for scatter plot
                            use_color = st.checkbox("Use color dimension", value=False)
                            if use_color and len(numeric_cols) > 2:
                                color_col = st.selectbox("Color by", numeric_cols, index=2 % len(numeric_cols))
                                scatter_fig = px.scatter(
                                    df, 
                                    x=x_col, 
                                    y=y_col,
                                    color=color_col,
                                    title=f"Scatter Plot: {x_col} vs {y_col} (colored by {color_col})"
                                )
                            else:
                                scatter_fig = px.scatter(
                                    df, 
                                    x=x_col, 
                                    y=y_col,
                                    title=f"Scatter Plot: {x_col} vs {y_col}"
                                )
                            st.plotly_chart(scatter_fig, use_container_width=True)
                            
                            # Add trendline option
                            if st.checkbox("Add trendline"):
                                try:
                                    trend_fig = px.scatter(
                                        df, 
                                        x=x_col, 
                                        y=y_col,
                                        title=f"Scatter Plot with Trendline: {x_col} vs {y_col}",
                                        trendline="ols"
                                    )
                                    st.plotly_chart(trend_fig, use_container_width=True)
                                except Exception as e:
                                    st.error(f"Error adding trendline: {e}")
                    else:
                        st.info("Need at least 2 numeric columns for scatter plots")
                        
                with viz_tabs[2]:  # Distribution Analysis
                    if numeric_cols:
                        dist_col = st.selectbox("Select column for distribution analysis", numeric_cols, key="dist_col")
                        
                        # Create histogram
                        hist_fig = px.histogram(
                            df, 
                            x=dist_col,
                            title=f"Histogram of {dist_col}",
                            nbins=st.slider("Number of bins", 5, 100, 20),
                            marginal=st.selectbox("Marginal plot", ["box", "violin", "rug", None])
                        )
                        st.plotly_chart(hist_fig, use_container_width=True)
                        
                        # Create box plot
                        box_fig = px.box(
                            df,
                            y=dist_col,
                            title=f"Box Plot of {dist_col}"
                        )
                        st.plotly_chart(box_fig, use_container_width=True)
                
                with viz_tabs[3]:  # Correlation Analysis
                    if len(numeric_cols) >= 2:
                        # Calculate correlation matrix
                        corr_method = st.radio("Correlation method", ["pearson", "spearman", "kendall"], horizontal=True)
                        corr_df = df[numeric_cols].corr(method=corr_method)
                        
                        # Create heatmap
                        heatmap_fig = px.imshow(
                            corr_df,
                            text_auto=True,
                            color_continuous_scale=st.selectbox(
                                "Color scale", 
                                ["RdBu_r", "Viridis", "Plasma", "Blues", "Reds"]
                            ),
                            title=f"Correlation Matrix ({corr_method.capitalize()})"
                        )
                        st.plotly_chart(heatmap_fig, use_container_width=True)
                        
                        # Show correlation values in table
                        with st.expander("Correlation Values"):
                            st.dataframe(corr_df.style.background_gradient(cmap="RdBu_r"), use_container_width=True)
            else:
                st.info("No numeric columns available for visualization.")
            
            st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.warning(f"Could not convert JSON to DataFrame: {str(e)}")
        st.code(str(json_data))

# Navigation with improved styling
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    if st.button ("← Back to Patient Data", key="back_data", type="secondary"):
        st.switch_page("pages/test_adminPatientData.py")
with col2:
    if st.button ("← Back to Patient List", key="back_list", type="secondary"):
        st.switch_page("pages/_admin_patient_info.py")
with col3:
    if st.button ("← Back to Dashboard", key="back_dashboard", type="secondary"):
        st.switch_page("pages/_admin_dashboard.py")
