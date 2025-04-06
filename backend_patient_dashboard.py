import streamlit as st
import pandas as pd
import plotly.express as px
import time
from backend_auth import get_db_connection
from datetime import datetime

# **Fetch Patient Data**
def get_patient_trials(patient_id):
    """Get count of completed trials for a patient"""
    conn = get_db_connection()
    if not conn:
        return 0
        
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM patient_trials 
                WHERE patient_id = %s AND end_time IS NOT NULL
            """, (patient_id,))
            count = cursor.fetchone()[0]
            return count
            
    except Exception as e:
        print(f"Error getting trial count: {str(e)}")
        return 0
    finally:
        conn.close()

# **Fetch Live Data**
def get_live_data(patient_id, limit=60):
    """Get live data for a patient with all parameters"""
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
                
            # Convert rows to dataframe
            data = []
            for row in rows:
                sensor_data, timestamp = row
                entry = {"Timestamp": timestamp, **sensor_data}
                data.append(entry)
            
            df = pd.DataFrame(data)
            return df.sort_values("Timestamp")
            
    except Exception as e:
        print(f"Error fetching live data: {str(e)}")
        return None
    finally:
        conn.close()

def start_trial(patient_id):
    """Start a new trial for a patient"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # Create new trial
            cursor.execute("""
                INSERT INTO patient_trials (patient_id, start_time)
                VALUES (%s, NOW())
                RETURNING trial_id
            """, (patient_id,))
            trial_id = cursor.fetchone()[0]
            conn.commit()
            
            # Store trial ID in session
            from streamlit import session_state
            session_state.current_trial_id = trial_id
            
            return True
            
    except Exception as e:
        print(f"Error starting trial: {str(e)}")
        return False
    finally:
        conn.close()

def end_trial(patient_id):
    """End current trial and save data"""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        with conn.cursor() as cursor:
            from streamlit import session_state
            trial_id = session_state.current_trial_id
            
            # Get all trial data
            cursor.execute("""
                SELECT sensor_data, timestamp 
                FROM live_patient_data 
                WHERE patient_id = %s 
                ORDER BY timestamp ASC
            """, (patient_id,))
            trial_data = cursor.fetchall()
            
            # Save trial data
            data_to_save = [
                {"sensor_data": row[0], "timestamp": row[1].isoformat()}
                for row in trial_data
            ]
            
            cursor.execute("""
                INSERT INTO patient_data (trial_id, patient_id, processed_data)
                VALUES (%s, %s, %s::jsonb)
            """, (trial_id, patient_id, data_to_save))
            
            # End trial
            cursor.execute("""
                UPDATE patient_trials 
                SET end_time = NOW()
                WHERE trial_id = %s
            """, (trial_id,))
            
            conn.commit()
            
            # Clear session trial ID
            del session_state.current_trial_id
            
            return True
            
    except Exception as e:
        print(f"Error ending trial: {str(e)}")
        return False
    finally:
        conn.close()