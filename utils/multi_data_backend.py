import pandas as pd
import streamlit as st
import numpy as np
import json
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from backend_patient_info import get_data_instance, get_db_connection
from scipy import stats
from scipy.signal import find_peaks
import statsmodels.api as sm
from statsmodels.nonparametric.smoothers_lowess import lowess
from plotly.subplots import make_subplots

# Functions extracted from Admin_multi_data.py
def get_patient_data_ids(patient_id):
    """Get all data IDs for a specific patient"""
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

def get_all_patients():
    """Get all patients"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT patient_id, username 
        FROM patients
        ORDER BY username
    """)
    patients = cursor.fetchall()
    cursor.close()
    conn.close()
    return patients

def load_data(data_id):
    """Load and process data for a specific data_id"""
    raw_data = get_data_instance(data_id)
    
    if not raw_data:
        return None
    
    # Convert tuple to dictionary with column names
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
        return None
    
    # Process the JSON data
    json_data = data_dict.get("data", "{}")
    
    # If it's a string, try to parse it as JSON
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except json.JSONDecodeError:
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
            return None
        
        # Add metadata columns
        df['data_id'] = data_id
        df['patient_id'] = data_dict.get('patient_id')
        df['username'] = data_dict.get('username')
        df['created_at'] = data_dict.get('created_at')
        
        return df
    except Exception as e:
        return None

# New timestamp normalization functions
def normalize_timestamps(df, timestamp_column, reference_time=None, unit='seconds'):
    """
    Normalize timestamps in a dataframe relative to a reference time.
    
    Args:
        df (pd.DataFrame): DataFrame containing timestamp data
        timestamp_column (str): Column name containing timestamps
        reference_time (datetime, optional): Reference time for normalization. 
                                            If None, uses the first timestamp.
        unit (str): Unit for normalized time ('seconds', 'minutes', 'hours')
    
    Returns:
        pd.DataFrame: DataFrame with normalized timestamp column added
    """
    if timestamp_column not in df.columns:
        return df.copy()
    
    # Create a copy to avoid modifying the original
    result_df = df.copy()
    
    # Convert timestamp column to datetime if it's not already
    if not pd.api.types.is_datetime64_any_dtype(result_df[timestamp_column]):
        try:
            result_df[timestamp_column] = pd.to_datetime(result_df[timestamp_column], errors='coerce')
        except:
            return df.copy()
    
    # Drop rows with invalid timestamps
    result_df = result_df.dropna(subset=[timestamp_column])
    
    if result_df.empty:
        return df.copy()
    
    # Set reference time if not provided
    if reference_time is None:
        reference_time = result_df[timestamp_column].min()
    
    # Calculate time difference
    time_diff = result_df[timestamp_column] - reference_time
    
    # Convert to specified unit
    if unit == 'seconds':
        result_df['normalized_time'] = time_diff.dt.total_seconds()
    elif unit == 'minutes':
        result_df['normalized_time'] = time_diff.dt.total_seconds() / 60
    elif unit == 'hours':
        result_df['normalized_time'] = time_diff.dt.total_seconds() / 3600
    else:
        result_df['normalized_time'] = time_diff.dt.total_seconds()
    
    return result_df

def align_multiple_datasets(data_frames, timestamp_columns, method='absolute', reference_time=None):
    """
    Align multiple dataframes based on their timestamps.
    
    Args:
        data_frames (dict): Dictionary of dataframes to align {data_id: dataframe}
        timestamp_columns (dict): Dictionary of timestamp column names for each dataframe {data_id: column_name}
        method (str): Alignment method ('absolute', 'relative')
        reference_time (datetime, optional): Reference time for absolute alignment
    
    Returns:
        dict: Dictionary of aligned dataframes with normalized timestamps
    """
    aligned_dfs = {}
    
    # For absolute alignment, use the provided reference time or find the global minimum
    if method == 'absolute':
        if reference_time is None:
            # Find the earliest timestamp across all dataframes
            min_times = []
            for data_id, df in data_frames.items():
                if data_id in timestamp_columns and timestamp_columns[data_id] in df.columns:
                    ts_col = timestamp_columns[data_id]
                    df_copy = df.copy()
                    if not pd.api.types.is_datetime64_any_dtype(df_copy[ts_col]):
                        try:
                            df_copy[ts_col] = pd.to_datetime(df_copy[ts_col], errors='coerce')
                            min_time = df_copy[ts_col].min()
                            if pd.notna(min_time):
                                min_times.append(min_time)
                        except:
                            continue
            
            if min_times:
                reference_time = min(min_times)
            else:
                reference_time = datetime.now()
        
        # Normalize each dataframe relative to the global reference time
        for data_id, df in data_frames.items():
            if data_id in timestamp_columns and timestamp_columns[data_id] in df.columns:
                aligned_dfs[data_id] = normalize_timestamps(df, timestamp_columns[data_id], reference_time)
            else:
                aligned_dfs[data_id] = df.copy()
    
    # For relative alignment, normalize each dataframe to its own start time
    elif method == 'relative':
        for data_id, df in data_frames.items():
            if data_id in timestamp_columns and timestamp_columns[data_id] in df.columns:
                aligned_dfs[data_id] = normalize_timestamps(df, timestamp_columns[data_id])
            else:
                aligned_dfs[data_id] = df.copy()
    
    return aligned_dfs

def merge_time_series(data_frames, value_columns, timestamp_columns, method='interpolate', freq='1s'):
    """
    Merge multiple time series dataframes into a single dataframe.
    
    Args:
        data_frames (dict): Dictionary of dataframes to merge {data_id: dataframe}
        value_columns (dict): Dictionary of value column names for each dataframe {data_id: column_name}
        timestamp_columns (dict): Dictionary of timestamp column names for each dataframe {data_id: column_name}
        method (str): Resampling method ('interpolate', 'ffill', 'nearest')
        freq (str): Frequency for resampling
    
    Returns:
        pd.DataFrame: Merged dataframe with aligned timestamps
    """
    # Create a list to store resampled dataframes
    resampled_dfs = []
    
    # Process each dataframe
    for data_id, df in data_frames.items():
        if (data_id in timestamp_columns and timestamp_columns[data_id] in df.columns and 
            data_id in value_columns and value_columns[data_id] in df.columns):
            
            ts_col = timestamp_columns[data_id]
            val_col = value_columns[data_id]
            
            # Create a copy and ensure timestamp is datetime
            df_copy = df.copy()
            if not pd.api.types.is_datetime64_any_dtype(df_copy[ts_col]):
                try:
                    df_copy[ts_col] = pd.to_datetime(df_copy[ts_col], errors='coerce')
                except:
                    continue
            
            # Drop rows with invalid timestamps
            df_copy = df_copy.dropna(subset=[ts_col])
            
            if not df_copy.empty:
                # Set timestamp as index
                df_copy = df_copy.set_index(ts_col)
                
                # Resample to the specified frequency
                resampled = df_copy[val_col].resample(freq)
                
                # Apply the specified method
                if method == 'interpolate':
                    resampled = resampled.interpolate(method='time')
                elif method == 'ffill':
                    resampled = resampled.ffill()
                elif method == 'nearest':
                    resampled = resampled.nearest()
                else:
                    resampled = resampled.mean()
                
                # Reset index to get timestamp as a column again
                resampled = resampled.reset_index()
                
                # Rename columns for clarity
                resampled.columns = [ts_col, f"{val_col}_{data_id}"]
                
                resampled_dfs.append(resampled)
    
    # If no valid dataframes, return empty dataframe
    if not resampled_dfs:
        return pd.DataFrame()
    
    # Merge all resampled dataframes on timestamp
    result = resampled_dfs[0]
    for i in range(1, len(resampled_dfs)):
        result = pd.merge_asof(
            result.sort_values(resampled_dfs[0].columns[0]),
            resampled_dfs[i].sort_values(resampled_dfs[i].columns[0]),
            left_on=resampled_dfs[0].columns[0],
            right_on=resampled_dfs[i].columns[0],
            direction='nearest'
        )
    
    return result

# Advanced visualization functions
def create_fft_analysis(df, param):
    """
    Perform Fast Fourier Transform analysis on a parameter
    
    Args:
        df (pd.DataFrame): DataFrame containing the data
        param (str): Column name of the parameter to analyze
    
    Returns:
        tuple: (frequencies, magnitudes, peaks)
    """
    if param not in df.columns:
        return None, None, None
    
    # Get the signal data
    signal = df[param].dropna().values
    
    if len(signal) < 4:  # Need at least a few points for FFT
        return None, None, None
    
    # Compute FFT
    n = len(signal)
    fft_result = np.fft.rfft(signal)
    fft_freq = np.fft.rfftfreq(n, 1)  # Assuming unit time steps
    fft_magnitude = np.abs(fft_result)
    
    # Find peaks
    peaks, _ = find_peaks(fft_magnitude, height=np.max(fft_magnitude)/10)
    
    return fft_freq, fft_magnitude, peaks

def create_trend_analysis(df, param, window=None):
    """
    Perform trend analysis using LOWESS smoothing
    
    Args:
        df (pd.DataFrame): DataFrame containing the data
        param (str): Column name of the parameter to analyze
        window (int, optional): Window size for smoothing
    
    Returns:
        tuple: (x_values, trend_values)
    """
    if param not in df.columns:
        return None, None
    
    # Get the data
    data = df[param].dropna()
    
    if len(data) < 4:  # Need at least a few points for trend analysis
        return None, None
    
    x = np.arange(len(data))
    y = data.values
    
    # Determine window size if not provided
    if window is None:
        window = max(3, len(data) // 5)
    
    # Calculate fraction for LOWESS
    frac = min(1.0, max(0.1, window / len(data)))
    
    # Perform LOWESS smoothing
    try:
        trend = lowess(y, x, frac=frac, it=1, return_sorted=False)
        return x, trend
    except:
        return None, None

def detect_outliers(df, param, method='zscore', threshold=3.0):
    """
    Detect outliers in a parameter
    
    Args:
        df (pd.DataFrame): DataFrame containing the data
        param (str): Column name of the parameter to analyze
        method (str): Method for outlier detection ('zscore', 'iqr')
        threshold (float): Threshold for outlier detection
    
    Returns:
        pd.Series: Boolean series indicating outliers
    """
    if param not in df.columns:
        return pd.Series(False, index=df.index)
    
    data = df[param].dropna()
    
    if len(data) < 4:  # Need at least a few points for outlier detection
        return pd.Series(False, index=df.index)
    
    outliers = pd.Series(False, index=data.index)
    
    if method == 'zscore':
        z_scores = np.abs(stats.zscore(data))
        outliers = z_scores > threshold
    elif method == 'iqr':
        q1 = data.quantile(0.25)
        q3 = data.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        outliers = (data < lower_bound) | (data > upper_bound)
    
    # Extend to full dataframe index
    full_outliers = pd.Series(False, index=df.index)
    full_outliers[outliers.index] = outliers
    
    return full_outliers

def calculate_cross_correlation(df1, param1, df2, param2, max_lag=None):
    """
    Calculate cross-correlation between two parameters
    
    Args:
        df1 (pd.DataFrame): First DataFrame
        param1 (str): Parameter from first DataFrame
        df2 (pd.DataFrame): Second DataFrame
        param2 (str): Parameter from second DataFrame
        max_lag (int, optional): Maximum lag to consider
    
    Returns:
        tuple: (lags, cross_correlation)
    """
    if param1 not in df1.columns or param2 not in df2.columns:
        return None, None
    
    # Get the data
    data1 = df1[param1].dropna().values
    data2 = df2[param2].dropna().values
    
    # Ensure both series have data
    if len(data1) < 2 or len(data2) < 2:
        return None, None
    
    # Determine max lag if not provided
    if max_lag is None:
        max_lag = min(len(data1), len(data2)) // 2
    
    # Calculate cross-correlation
    try:
        cross_corr = np.correlate(data1 - np.mean(data1), data2 - np.mean(data2), mode='full')
        # Normalize
        cross_corr = cross_corr / (np.std(data1) * np.std(data2) * len(data1))
        
        # Get lags
        lags = np.arange(-max_lag, max_lag + 1)
        mid = len(cross_corr) // 2
        cross_corr = cross_corr[mid-max_lag:mid+max_lag+1]
        
        return lags, cross_corr
    except:
        return None, None


# Helper functions for UI
def reset_selections():
    """Reset all selections and loaded data"""
    st.session_state.selected_data_ids = []
    st.session_state.loaded_data = {}
    st.session_state.timestamp_columns = {}
    st.session_state.value_columns = {}
    st.session_state.normalized_data = {}
    st.session_state.merged_data = None

def load_selected_data():
    """Load data for all selected data IDs"""
    for data_id in st.session_state.selected_data_ids:
        if data_id not in st.session_state.loaded_data:
            df = load_data(data_id)
            if df is not None:
                st.session_state.loaded_data[data_id] = df

def get_numeric_columns(df):
    """Get all numeric columns from a dataframe"""
    return df.select_dtypes(include=['number']).columns.tolist()

def get_datetime_columns(df):
    """Get all potential datetime columns from a dataframe"""
    datetime_cols = df.select_dtypes(include=['datetime']).columns.tolist()
    
    # Also check string columns that might be convertible to datetime
    for col in df.select_dtypes(include=['object']).columns:
        try:
            pd.to_datetime(df[col], errors='raise')
            datetime_cols.append(col)
        except:
            pass
    
    return datetime_cols

def create_visualization(viz_type, data_frames, params, timestamp_cols=None, options=None):
    """Create visualization based on selected type and parameters"""
    if not data_frames or not params:
        return None
    
    if options is None:
        options = {}
    
    # Basic line chart
    if viz_type == "Line Chart":
        fig = go.Figure()
        for data_id, param in params.items():
            if data_id in data_frames and param in data_frames[data_id].columns:
                df = data_frames[data_id]
                
                # Use timestamp column if provided, otherwise use index
                if timestamp_cols and data_id in timestamp_cols and timestamp_cols[data_id] in df.columns:
                    x_values = df[timestamp_cols[data_id]]
                else:
                    x_values = df.index
                
                # Add trace with hover data
                hover_text = [f"Data ID: {data_id}<br>Value: {val}" for val in df[param]]
                fig.add_trace(go.Scatter(
                    x=x_values,
                    y=df[param],
                    mode='lines+markers',
                    name=f"{param} (ID: {data_id})",
                    hoverinfo="text",
                    hovertext=hover_text
                ))
        
        fig.update_layout(
            title="Multi-Data Line Chart",
            xaxis_title="Time/Index",
            yaxis_title="Value",
            legend_title="Parameters"
        )
        return fig
    
    # Scatter plot
    elif viz_type == "Scatter Plot":
        fig = go.Figure()
        for data_id, param in params.items():
            if data_id in data_frames and param in data_frames[data_id].columns:
                df = data_frames[data_id]
                
                # Use timestamp column if provided, otherwise use index
                if timestamp_cols and data_id in timestamp_cols and timestamp_cols[data_id] in df.columns:
                    x_values = df[timestamp_cols[data_id]]
                else:
                    x_values = df.index
                
                fig.add_trace(go.Scatter(
                    x=x_values,
                    y=df[param],
                    mode='markers',
                    name=f"{param} (ID: {data_id})",
                    marker=dict(size=8)
                ))
        
        fig.update_layout(
            title="Multi-Data Scatter Plot",
            xaxis_title="Time/Index",
            yaxis_title="Value",
            legend_title="Parameters"
        )
        return fig
    
    # Box plot
    elif viz_type == "Box Plot":
        data = []
        for data_id, param in params.items():
            if data_id in data_frames and param in data_frames[data_id].columns:
                df = data_frames[data_id]
                values = df[param].dropna()
                if not values.empty:
                    data.append({
                        'y': values,
                        'type': 'box',
                        'name': f"{param} (ID: {data_id})"
                    })
        
        if data:
            fig = go.Figure(data=data)
            fig.update_layout(
                title="Multi-Data Box Plot",
                yaxis_title="Value",
                showlegend=False
            )
            return fig
        return None
    
    # Histogram
    elif viz_type == "Histogram":
        fig = go.Figure()
        for data_id, param in params.items():
            if data_id in data_frames and param in data_frames[data_id].columns:
                df = data_frames[data_id]
                values = df[param].dropna()
                if not values.empty:
                    fig.add_trace(go.Histogram(
                        x=values,
                        name=f"{param} (ID: {data_id})",
                        opacity=0.7,
                        nbinsx=options.get('bins', 30)
                    ))
        
        fig.update_layout(
            title="Multi-Data Histogram",
            xaxis_title="Value",
            yaxis_title="Count",
            barmode='overlay',
            legend_title="Parameters"
        )
        return fig
    
    # Heatmap
    elif viz_type == "Correlation Heatmap":
        # Prepare data for correlation
        all_data = {}
        for data_id, param in params.items():
            if data_id in data_frames and param in data_frames[data_id].columns:
                df = data_frames[data_id]
                all_data[f"{param} (ID: {data_id})"] = df[param].values
        
        # Create DataFrame from all selected parameters
        corr_df = pd.DataFrame(all_data)
        
        # Calculate correlation matrix
        corr_matrix = corr_df.corr(method=options.get('corr_method', 'pearson'))
        
        # Create heatmap
        fig = px.imshow(
            corr_matrix,
            text_auto=True,
            color_continuous_scale=options.get('colorscale', 'RdBu_r'),
            zmin=-1, zmax=1,
            title="Correlation Heatmap"
        )
        
        fig.update_layout(
            xaxis_title="Parameters",
            yaxis_title="Parameters"
        )
        return fig
    
    # Advanced: FFT Analysis
    elif viz_type == "FFT Analysis":
        fig = make_subplots(rows=len(params), cols=1, 
                           subplot_titles=[f"FFT Analysis - {param} (ID: {data_id})" 
                                          for data_id, param in params.items()])
        
        row = 1
        for data_id, param in params.items():
            if data_id in data_frames and param in data_frames[data_id].columns:
                df = data_frames[data_id]
                
                # Perform FFT analysis
                freqs, mags, peaks = create_fft_analysis(df, param)
                
                if freqs is not None and mags is not None:
                    # Add FFT magnitude trace
                    fig.add_trace(
                        go.Scatter(
                            x=freqs,
                            y=mags,
                            mode='lines',
                            name=f"FFT {param} (ID: {data_id})"
                        ),
                        row=row, col=1
                    )
                    
                    # Add peak markers if any
                    if peaks is not None and len(peaks) > 0:
                        fig.add_trace(
                            go.Scatter(
                                x=freqs[peaks],
                                y=mags[peaks],
                                mode='markers',
                                marker=dict(size=8, color='red'),
                                name=f"Peaks {param} (ID: {data_id})"
                            ),
                            row=row, col=1
                        )
                    
                    # Update axes labels
                    fig.update_xaxes(title_text="Frequency", row=row, col=1)
                    fig.update_yaxes(title_text="Magnitude", row=row, col=1)
                    
                    row += 1
        
        fig.update_layout(
            height=300 * len(params),
            title_text="FFT Analysis",
            showlegend=True
        )
        return fig
    
    # Advanced: Trend Analysis
    elif viz_type == "Trend Analysis":
        fig = make_subplots(rows=len(params), cols=1, 
                           subplot_titles=[f"Trend Analysis - {param} (ID: {data_id})" 
                                          for data_id, param in params.items()])
        
        row = 1
        for data_id, param in params.items():
            if data_id in data_frames and param in data_frames[data_id].columns:
                df = data_frames[data_id]
                
                # Get original data
                data = df[param].dropna()
                x_orig = np.arange(len(data))
                
                # Add original data trace
                fig.add_trace(
                    go.Scatter(
                        x=x_orig,
                        y=data.values,
                        mode='markers',
                        name=f"Data {param} (ID: {data_id})",
                        marker=dict(size=5, opacity=0.5)
                    ),
                    row=row, col=1
                )
                
                # Perform trend analysis
                window = options.get('window', None)
                x_trend, trend = create_trend_analysis(df, param, window)
                
                if x_trend is not None and trend is not None:
                    # Add trend line
                    fig.add_trace(
                        go.Scatter(
                            x=x_trend,
                            y=trend,
                            mode='lines',
                            name=f"Trend {param} (ID: {data_id})",
                            line=dict(width=2, color='red')
                        ),
                        row=row, col=1
                    )
                
                # Update axes labels
                fig.update_xaxes(title_text="Index", row=row, col=1)
                fig.update_yaxes(title_text="Value", row=row, col=1)
                
                row += 1
        
        fig.update_layout(
            height=300 * len(params),
            title_text="Trend Analysis",
            showlegend=True
        )
        return fig
    
    # Advanced: Outlier Detection
    elif viz_type == "Outlier Detection":
        fig = make_subplots(rows=len(params), cols=1, 
                           subplot_titles=[f"Outlier Detection - {param} (ID: {data_id})" 
                                          for data_id, param in params.items()])
        
        row = 1
        for data_id, param in params.items():
            if data_id in data_frames and param in data_frames[data_id].columns:
                df = data_frames[data_id]
                
                # Use timestamp column if provided, otherwise use index
                if timestamp_cols and data_id in timestamp_cols and timestamp_cols[data_id] in df.columns:
                    x_values = df[timestamp_cols[data_id]]
                else:
                    x_values = np.arange(len(df))
                
                # Get data and detect outliers
                method = options.get('outlier_method', 'zscore')
                threshold = options.get('outlier_threshold', 3.0)
                outliers = detect_outliers(df, param, method, threshold)
                
                # Add normal points
                normal_mask = ~outliers
                fig.add_trace(
                    go.Scatter(
                        x=x_values[normal_mask],
                        y=df[param][normal_mask],
                        mode='markers',
                        name=f"Normal {param} (ID: {data_id})",
                        marker=dict(size=6, color='blue')
                    ),
                    row=row, col=1
                )
                
                # Add outlier points
                if outliers.any():
                    fig.add_trace(
                        go.Scatter(
                            x=x_values[outliers],
                            y=df[param][outliers],
                            mode='markers',
                            name=f"Outliers {param} (ID: {data_id})",
                            marker=dict(size=10, color='red', symbol='x')
                        ),
                        row=row, col=1
                    )
                
                # Update axes labels
                fig.update_xaxes(title_text="Time/Index", row=row, col=1)
                fig.update_yaxes(title_text="Value", row=row, col=1)
                
                row += 1
        
        fig.update_layout(
            height=300 * len(params),
            title_text=f"Outlier Detection (Method: {options.get('outlier_method', 'zscore')}, Threshold: {options.get('outlier_threshold', 3.0)})",
            showlegend=True
        )
        return fig
    
    # Advanced: Cross-Correlation
    elif viz_type == "Cross-Correlation":
        if len(params) < 2:
            st.warning("Cross-correlation requires at least two parameters")
            return None
        
        # Get all parameter pairs
        param_pairs = []
        data_ids = list(params.keys())
        for i in range(len(data_ids)):
            for j in range(i+1, len(data_ids)):
                param_pairs.append((data_ids[i], params[data_ids[i]], data_ids[j], params[data_ids[j]]))
        
        # Create subplots
        fig = make_subplots(rows=len(param_pairs), cols=1, 
                           subplot_titles=[f"Cross-Correlation: {param1} (ID: {id1}) vs {param2} (ID: {id2})" 
                                          for id1, param1, id2, param2 in param_pairs])
        
        row = 1
        for id1, param1, id2, param2 in param_pairs:
            if (id1 in data_frames and param1 in data_frames[id1].columns and
                id2 in data_frames and param2 in data_frames[id2].columns):
                
                # Calculate cross-correlation
                max_lag = options.get('max_lag', None)
                lags, cross_corr = calculate_cross_correlation(
                    data_frames[id1], param1, 
                    data_frames[id2], param2, 
                    max_lag
                )
                
                if lags is not None and cross_corr is not None:
                    # Add cross-correlation trace
                    fig.add_trace(
                        go.Scatter(
                            x=lags,
                            y=cross_corr,
                            mode='lines+markers',
                            name=f"{param1} (ID: {id1}) vs {param2} (ID: {id2})"
                        ),
                        row=row, col=1
                    )
                    
                    # Find max correlation and its lag
                    max_idx = np.argmax(np.abs(cross_corr))
                    max_corr = cross_corr[max_idx]
                    max_lag = lags[max_idx]
                    
                    # Add marker for max correlation
                    fig.add_trace(
                        go.Scatter(
                            x=[max_lag],
                            y=[max_corr],
                            mode='markers',
                            marker=dict(size=10, color='red'),
                            name=f"Max Correlation: {max_corr:.3f} at lag {max_lag}"
                        ),
                        row=row, col=1
                    )
                    
                    # Add zero lag line
                    fig.add_shape(
                        type="line",
                        x0=0, y0=min(cross_corr), x1=0, y1=max(cross_corr),
                        line=dict(color="gray", width=1, dash="dash"),
                        row=row, col=1
                    )
                    
                    # Update axes labels
                    fig.update_xaxes(title_text="Lag", row=row, col=1)
                    fig.update_yaxes(title_text="Correlation", row=row, col=1)
                    
                    row += 1
        
        fig.update_layout(
            height=300 * len(param_pairs),
            title_text="Cross-Correlation Analysis",
            showlegend=True
        )
        return fig
    
    # Advanced: 3D Scatter Plot
    elif viz_type == "3D Scatter Plot":
        if len(params) < 3:
            st.warning("3D scatter plot requires at least three parameters")
            return None
        
        # Get the first three parameters
        data_ids = list(params.keys())[:3]
        param_names = [params[data_id] for data_id in data_ids]
        
        # Extract data
        x_data = data_frames[data_ids[0]][param_names[0]].values if data_ids[0] in data_frames else []
        y_data = data_frames[data_ids[1]][param_names[1]].values if data_ids[1] in data_frames else []
        z_data = data_frames[data_ids[2]][param_names[2]].values if data_ids[2] in data_frames else []
        
        # Ensure all arrays have the same length
        min_len = min(len(x_data), len(y_data), len(z_data))
        x_data = x_data[:min_len]
        y_data = y_data[:min_len]
        z_data = z_data[:min_len]
        
        if min_len > 0:
            fig = go.Figure(data=[go.Scatter3d(
                x=x_data,
                y=y_data,
                z=z_data,
                mode='markers',
                marker=dict(
                    size=5,
                    color=z_data,
                    colorscale='Viridis',
                    opacity=0.8
                )
            )])
            
            fig.update_layout(
                title=f"3D Scatter Plot",
                scene=dict(
                    xaxis_title=f"{param_names[0]} (ID: {data_ids[0]})",
                    yaxis_title=f"{param_names[1]} (ID: {data_ids[1]})",
                    zaxis_title=f"{param_names[2]} (ID: {data_ids[2]})"
                )
            )
            return fig
        return None
    
    # Advanced: Normalized Time Series
    elif viz_type == "Normalized Time Series":
        if not timestamp_cols:
            st.warning("Timestamp columns must be selected for normalized time series")
            return None
        
        fig = go.Figure()
        for data_id, param in params.items():
            if (data_id in data_frames and param in data_frames[data_id].columns and
                data_id in timestamp_cols and timestamp_cols[data_id] in data_frames[data_id].columns):
                
                # Get normalized data if available
                if data_id in st.session_state.normalized_data:
                    df = st.session_state.normalized_data[data_id]
                else:
                    # Normalize timestamps
                    df = normalize_timestamps(
                        data_frames[data_id], 
                        timestamp_cols[data_id],
                        unit=options.get('time_unit', 'seconds')
                    )
                    st.session_state.normalized_data[data_id] = df
                
                if 'normalized_time' in df.columns:
                    # Add trace
                    fig.add_trace(go.Scatter(
                        x=df['normalized_time'],
                        y=df[param],
                        mode='lines+markers',
                        name=f"{param} (ID: {data_id})"
                    ))
        
        # Update layout
        time_unit = options.get('time_unit', 'seconds')
        fig.update_layout(
            title="Normalized Time Series",
            xaxis_title=f"Time ({time_unit} from reference)",
            yaxis_title="Value",
            legend_title="Parameters"
        )
        return fig
    
    # Advanced: Merged Time Series
    elif viz_type == "Merged Time Series":
        if not timestamp_cols or not st.session_state.value_columns:
            st.warning("Timestamp and value columns must be selected for merged time series")
            return None
        
        # Merge time series if not already done
        if st.session_state.merged_data is None:
            merged_df = merge_time_series(
                data_frames,
                st.session_state.value_columns,
                timestamp_cols,
                method=options.get('resample_method', 'interpolate'),
                freq=options.get('resample_freq', '1s')
            )
            st.session_state.merged_data = merged_df
        else:
            merged_df = st.session_state.merged_data
        
        if merged_df.empty:
            st.warning("Could not merge time series data")
            return None
        
        # Create figure
        fig = go.Figure()
        
        # Get timestamp column (first column)
        ts_col = merged_df.columns[0]
        
        # Add traces for each value column
        for col in merged_df.columns[1:]:
            fig.add_trace(go.Scatter(
                x=merged_df[ts_col],
                y=merged_df[col],
                mode='lines',
                name=col
            ))
        
        # Update layout
        fig.update_layout(
            title=f"Merged Time Series (Method: {options.get('resample_method', 'interpolate')}, Freq: {options.get('resample_freq', '1s')})",
            xaxis_title="Time",
            yaxis_title="Value",
            legend_title="Parameters"
        )
        return fig
    
    return None
