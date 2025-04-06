
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
import time
from utils.multi_data_backend import (
    get_patient_data_ids, get_all_patients, load_data,
    normalize_timestamps, align_multiple_datasets, merge_time_series,
    create_fft_analysis, create_trend_analysis, detect_outliers, calculate_cross_correlation,
    reset_selections, load_selected_data, get_numeric_columns, get_datetime_columns, create_visualization,
)

# Set page configuration
st.set_page_config(page_title="Multi-Data Analysis", layout="wide")

# Initialize session state variables if they don't exist
if 'selected_data_ids' not in st.session_state:
    st.session_state.selected_data_ids = []
if 'loaded_data' not in st.session_state:
    st.session_state.loaded_data = {}
if 'timestamp_columns' not in st.session_state:
    st.session_state.timestamp_columns = {}
if 'value_columns' not in st.session_state:
    st.session_state.value_columns = {}
if 'normalized_data' not in st.session_state:
    st.session_state.normalized_data = {}
if 'merged_data' not in st.session_state:
    st.session_state.merged_data = None


# Main app layout
st.title("Advanced Multi-Data Analysis")

# Sidebar for data selection
with st.sidebar:
    st.header("Data Selection")
    
    # Patient selection
    patients = get_all_patients()
    patient_options = {str(p[0]): p[1] for p in patients}
    selected_patient = st.selectbox(
        "Select Patient",
        options=list(patient_options.keys()),
        format_func=lambda x: patient_options[x]
    )
    
    # Get data IDs for selected patient
    if selected_patient:
        data_ids = get_patient_data_ids(selected_patient)
        data_id_options = {str(d[0]): f"{d[0]} ({d[1].strftime('%Y-%m-%d %H:%M')})" for d in data_ids}
        
        # Multi-select for data IDs
        selected_data_ids = st.multiselect(
            "Select Data IDs",
            options=list(data_id_options.keys()),
            format_func=lambda x: data_id_options[x]
        )
        
        # Update session state
        st.session_state.selected_data_ids = selected_data_ids
        
        # Load button
        if st.button("Load Selected Data"):
            load_selected_data()
            st.success(f"Loaded {len(st.session_state.loaded_data)} datasets")
    
    # Reset button
    if st.button("Reset All"):
        reset_selections()
        st.success("All selections reset")

    if st.button ("Return to Dashboard"):
        st.switch_page("pages/_admin_dashboard.py")

# Main content area
if st.session_state.selected_data_ids and st.session_state.loaded_data:
    # Display tabs for different functionalities
    tabs = st.tabs(["Data Preview", "Basic Visualization", "Advanced Visualization", "Time Series Analysis"])
    
    # Tab 1: Data Preview
    with tabs[0]:
        st.header("Data Preview")
        
        # Select dataset to preview
        preview_data_id = st.selectbox(
            "Select Dataset to Preview",
            options=st.session_state.selected_data_ids,
            format_func=lambda x: f"Data ID: {x}"
        )
        
        if preview_data_id in st.session_state.loaded_data:
            df = st.session_state.loaded_data[preview_data_id]
            st.write(f"Dataset Shape: {df.shape}")
            st.dataframe(df.head(10))
            
            # Show column info
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Numeric Columns")
                numeric_cols = get_numeric_columns(df)
                st.write(", ".join(numeric_cols) if numeric_cols else "None")
            
            with col2:
                st.subheader("Datetime Columns")
                datetime_cols = get_datetime_columns(df)
                st.write(", ".join(datetime_cols) if datetime_cols else "None")
    
    # Tab 2: Basic Visualization
    with tabs[1]:
        st.header("Basic Visualization")
        
        # Select visualization type
        viz_type = st.selectbox(
            "Select Visualization Type",
            options=["Line Chart", "Scatter Plot", "Box Plot", "Histogram", "Correlation Heatmap"]
        )
        
        # Parameter selection for each dataset
        st.subheader("Select Parameters")
        
        params = {}
        for data_id in st.session_state.selected_data_ids:
            if data_id in st.session_state.loaded_data:
                df = st.session_state.loaded_data[data_id]
                numeric_cols = get_numeric_columns(df)
                
                if numeric_cols:
                    selected_param = st.selectbox(
                        f"Parameter for Data ID {data_id}",
                        options=["None"] + numeric_cols,
                        key=f"basic_param_{data_id}"
                    )
                    
                    if selected_param != "None":
                        params[data_id] = selected_param
        
        # Visualization options
        with st.expander("Visualization Options"):
            options = {}
            
            if viz_type == "Histogram":
                options['bins'] = st.slider("Number of Bins", min_value=5, max_value=100, value=30)
            
            elif viz_type == "Correlation Heatmap":
                options['corr_method'] = st.selectbox(
                    "Correlation Method",
                    options=["pearson", "spearman", "kendall"],
                    index=0
                )
                options['colorscale'] = st.selectbox(
                    "Color Scale",
                    options=["RdBu_r", "Viridis", "Plasma", "Inferno", "Magma"],
                    index=0
                )
        
        # Create and display visualization
        if params:
            fig = create_visualization(viz_type, st.session_state.loaded_data, params, options=options)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Could not create visualization with selected parameters")
        else:
            st.warning("Please select at least one parameter")
    
    # Tab 3: Advanced Visualization
    with tabs[2]:
        st.header("Advanced Visualization")
        
        # Select visualization type
        adv_viz_type = st.selectbox(
            "Select Advanced Visualization Type",
            options=[
                "FFT Analysis", "Trend Analysis", "Outlier Detection", 
                "Cross-Correlation", "3D Scatter Plot"
            ]
        )
        
        # Parameter selection for each dataset
        st.subheader("Select Parameters")
        
        adv_params = {}
        for data_id in st.session_state.selected_data_ids:
            if data_id in st.session_state.loaded_data:
                df = st.session_state.loaded_data[data_id]
                numeric_cols = get_numeric_columns(df)
                
                if numeric_cols:
                    selected_param = st.selectbox(
                        f"Parameter for Data ID {data_id}",
                        options=["None"] + numeric_cols,
                        key=f"adv_param_{data_id}"
                    )
                    
                    if selected_param != "None":
                        adv_params[data_id] = selected_param
        
        # Advanced visualization options
        with st.expander("Advanced Options"):
            adv_options = {}
            
            if adv_viz_type == "Trend Analysis":
                adv_options['window'] = st.slider(
                    "Smoothing Window Size", 
                    min_value=3, 
                    max_value=50, 
                    value=10,
                    help="Larger values create smoother trends"
                )
            
            elif adv_viz_type == "Outlier Detection":
                adv_options['outlier_method'] = st.selectbox(
                    "Outlier Detection Method",
                    options=["zscore", "iqr"],
                    index=0,
                    help="Z-score uses standard deviations, IQR uses interquartile range"
                )
                adv_options['outlier_threshold'] = st.slider(
                    "Outlier Threshold", 
                    min_value=1.0, 
                    max_value=5.0, 
                    value=3.0,
                    step=0.1,
                    help="Lower values detect more outliers"
                )
            
            elif adv_viz_type == "Cross-Correlation":
                adv_options['max_lag'] = st.slider(
                    "Maximum Lag", 
                    min_value=5, 
                    max_value=100, 
                    value=20,
                    help="Maximum lag to consider in cross-correlation"
                )
        
        # Create and display advanced visualization
        if adv_params:
            fig = create_visualization(adv_viz_type, st.session_state.loaded_data, adv_params, options=adv_options)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Could not create visualization with selected parameters")
        else:
            st.warning("Please select at least one parameter")
    
    # Tab 4: Time Series Analysis
    with tabs[3]:
        st.header("Time Series Analysis")
        
        # Timestamp column selection for each dataset
        st.subheader("Select Timestamp Columns")
        
        # Collect all timestamp columns across datasets
        all_timestamp_cols = set()
        for data_id in st.session_state.selected_data_ids:
            if data_id in st.session_state.loaded_data:
                df = st.session_state.loaded_data[data_id]
                datetime_cols = get_datetime_columns(df)
                all_timestamp_cols.update(datetime_cols)
        
        # Multiselect for timestamp columns with "All" option
        timestamp_options = ["None", "All"] + list(all_timestamp_cols)
        selected_timestamp_cols = st.multiselect(
            "Select timestamp columns for normalization",
            options=timestamp_options,
            default=["None"],
            help="Select the columns containing timestamps to normalize data across patients. Choose 'All' to normalize all timestamp columns."
        )
        
        # Process the timestamp selection
        timestamp_columns = {}
        if "None" not in selected_timestamp_cols:
            if "All" in selected_timestamp_cols:
                # If "All" is selected, use all timestamp columns for each dataset
                for data_id in st.session_state.selected_data_ids:
                    if data_id in st.session_state.loaded_data:
                        df = st.session_state.loaded_data[data_id]
                        datetime_cols = get_datetime_columns(df)
                        if datetime_cols:
                            timestamp_columns[data_id] = datetime_cols[0]  # Use the first datetime column
            else:
                # Let user select which timestamp column to use for each dataset
                for data_id in st.session_state.selected_data_ids:
                    if data_id in st.session_state.loaded_data:
                        df = st.session_state.loaded_data[data_id]
                        datetime_cols = [col for col in get_datetime_columns(df) if col in selected_timestamp_cols]
                        if datetime_cols:
                            timestamp_col = st.selectbox(
                                f"Timestamp column for Data ID {data_id}",
                                options=datetime_cols,
                                key=f"ts_col_{data_id}"
                            )
                            timestamp_columns[data_id] = timestamp_col
        
        # Update session state
        st.session_state.timestamp_columns = timestamp_columns
        
        # Value column selection for each dataset
        st.subheader("Select Value Columns")
        
        value_columns = {}
        for data_id in st.session_state.selected_data_ids:
            if data_id in st.session_state.loaded_data:
                df = st.session_state.loaded_data[data_id]
                numeric_cols = get_numeric_columns(df)
                
                if numeric_cols:
                    value_col = st.selectbox(
                        f"Value column for Data ID {data_id}",
                        options=["None"] + numeric_cols,
                        key=f"val_col_{data_id}"
                    )
                    
                    if value_col != "None":
                        value_columns[data_id] = value_col
        
        # Update session state
        st.session_state.value_columns = value_columns
        
        # Time series analysis options
        st.subheader("Time Series Analysis Options")
        
        ts_viz_type = st.selectbox(
            "Select Time Series Analysis Type",
            options=["Normalized Time Series", "Merged Time Series"]
        )
        
        with st.expander("Time Series Options"):
            ts_options = {}
            
            if ts_viz_type == "Normalized Time Series":
                ts_options['time_unit'] = st.selectbox(
                    "Time Unit",
                    options=["seconds", "minutes", "hours"],
                    index=0
                )
                
                ts_options['alignment'] = st.selectbox(
                    "Alignment Method",
                    options=["absolute", "relative"],
                    index=0,
                    help="Absolute: align to global reference time, Relative: align each series to its own start"
                )
                
                if ts_options['alignment'] == "absolute":
                    use_custom_ref = st.checkbox("Use custom reference time", value=False)
                    if use_custom_ref:
                        ref_date = st.date_input("Reference date", value=datetime.now().date())
                        ref_time = st.time_input("Reference time", value=datetime.now().time())
                        ts_options['reference_time'] = datetime.combine(ref_date, ref_time)
            
            elif ts_viz_type == "Merged Time Series":
                ts_options['resample_method'] = st.selectbox(
                    "Resampling Method",
                    options=["interpolate", "ffill", "nearest"],
                    index=0,
                    help="Method to fill gaps in merged time series"
                )
                
                ts_options['resample_freq'] = st.selectbox(
                    "Resampling Frequency",
                    options=["1s", "5s", "10s", "30s", "1min", "5min", "10min", "30min", "1h"],
                    index=0,
                    help="Time frequency for resampling"
                )
        
        # Create and display time series visualization
        if timestamp_columns and value_columns:
            # Normalize timestamps if needed
            if ts_viz_type == "Normalized Time Series":
                # Clear previous normalized data
                st.session_state.normalized_data = {}
                
                # Normalize each dataset
                for data_id in timestamp_columns:
                    if data_id in st.session_state.loaded_data and data_id in value_columns:
                        df = st.session_state.loaded_data[data_id]
                        ts_col = timestamp_columns[data_id]
                        
                        # Normalize timestamps
                        if ts_options['alignment'] == "absolute" and 'reference_time' in ts_options:
                            normalized_df = normalize_timestamps(
                                df, ts_col, 
                                reference_time=ts_options['reference_time'],
                                unit=ts_options['time_unit']
                            )
                        else:
                            normalized_df = normalize_timestamps(
                                df, ts_col, 
                                unit=ts_options['time_unit']
                            )
                        
                        st.session_state.normalized_data[data_id] = normalized_df
                
                # Create visualization
                fig = create_visualization(
                    ts_viz_type, 
                    st.session_state.loaded_data, 
                    value_columns, 
                    timestamp_cols=timestamp_columns,
                    options=ts_options
                )
                
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Could not create time series visualization")
            
            elif ts_viz_type == "Merged Time Series":
                # Merge time series
                merged_df = merge_time_series(
                    st.session_state.loaded_data,
                    value_columns,
                    timestamp_columns,
                    method=ts_options['resample_method'],
                    freq=ts_options['resample_freq']
                )
                
                # Store merged data
                st.session_state.merged_data = merged_df
                
                if not merged_df.empty:
                    # Display merged dataframe
                    st.subheader("Merged Time Series Data")
                    st.dataframe(merged_df.head(10))
                    
                    # Create visualization
                    fig = create_visualization(
                        ts_viz_type, 
                        st.session_state.loaded_data, 
                        value_columns, 
                        timestamp_cols=timestamp_columns,
                        options=ts_options
                    )
                    
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Could not create merged time series visualization")
                else:
                    st.warning("Could not merge time series data")
        else:
            st.warning("Please select timestamp and value columns for time series analysis")
else:
    st.info("Please select and load data from the sidebar to begin analysis")
