import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from utils.security import require_admin_auth, is_admin_authenticated
from admin_dashboard_backend import get_pending_comments, add_comment, get_pending_comment_cases
from backend_auth import get_db_connection

st.set_page_config(page_title="Patient Comments Editor", layout="wide")

# Check authentication
if not is_admin_authenticated():
    st.error("⚠️ Access Denied: Admin authentication required")
    st.warning("Please log in to access data.")
    if st.button("Go to Login"):
        st.switch_page("pages/_admin_auth.py")
    st.stop()

# Function to get patient data with comments
def get_patient_data_with_comments():
    """Get all patient data with their comments"""
    conn = get_db_connection()
    if not conn:
        st.error("Database connection error!")
        return []
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Join patient_data with patient_comments and patients tables
        cursor.execute("""
            SELECT pd.data_id, pd.patient_id, p.username, pc.comment, 
                   pd.created_at, pc.timestamp as comment_date
            FROM patient_data pd
            LEFT JOIN patient_comments pc ON pd.data_id = pc.data_id
            LEFT JOIN patients p ON pd.patient_id = p.patient_id
            ORDER BY pd.created_at DESC
        """)
        data = cursor.fetchall()
        return data
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# Function to get data for a specific patient
def get_patient_data_by_id(patient_id):
    """Get data for a specific patient with comments"""
    conn = get_db_connection()
    if not conn:
        st.error("Database connection error!")
        return []
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT pd.data_id, pd.patient_id, p.username, pc.comment, 
                   pd.created_at, pc.created_at as comment_date
            FROM patient_data pd
            LEFT JOIN patient_comments pc ON pd.data_id = pc.data_id
            LEFT JOIN patients p ON pd.patient_id = p.patient_id
            WHERE pd.patient_id = %s
            ORDER BY pd.created_at DESC
        """, (patient_id,))
        data = cursor.fetchall()
        return data
    except Exception as e:
        st.error(f"Error fetching data for patient {patient_id}: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# Function to update a comment
def update_comment(data_id, patient_id, new_comment):
    """Update an existing comment or add if it doesn't exist"""
    conn = get_db_connection()
    if not conn:
        st.error("Database connection error!")
        return False
    
    cursor = conn.cursor()
    
    try:
        # Check if comment exists
        cursor.execute("""
            SELECT COUNT(*) FROM patient_comments 
            WHERE data_id = %s
        """, (data_id,))
        
        comment_exists = cursor.fetchone()[0] > 0
        
        if comment_exists:
            # Update existing comment
            cursor.execute("""
                UPDATE patient_comments
                SET comment = %s
                WHERE data_id = %s
            """, (new_comment, data_id))
        else:
            # Add new comment using the imported function
            add_comment(data_id, patient_id, new_comment)
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error updating comment: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Function to delete a comment
def delete_comment(data_id):
    """Delete a comment"""
    conn = get_db_connection()
    if not conn:
        st.error("Database connection error!")
        return False
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            DELETE FROM patient_comments
            WHERE data_id = %s
        """, (data_id,))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error deleting comment: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Function to get all patients
def get_all_patients():
    """Get all patients"""
    conn = get_db_connection()
    if not conn:
        st.error("Database connection error!")
        return []
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT patient_id, username 
            FROM patients
            ORDER BY username
        """)
        patients = cursor.fetchall()
        return patients
    except Exception as e:
        st.error(f"Error fetching patients: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# Title
st.title("Patient Comments Editor")

# Get pending comments count
pending_count = get_pending_comments()
if isinstance(pending_count, int):
    st.info(f"There are {pending_count} patient data entries without comments.")

# Get all patients for filtering
all_patients = get_all_patients()
patient_options = {p['patient_id']: f"{p['username']} (ID: {p['patient_id']})" for p in all_patients}
patient_options['all'] = "All Patients"

# Patient filter
selected_patient = st.selectbox(
    "Filter by Patient",
    options=['all'] + list(patient_options.keys()),
    format_func=lambda x: patient_options[x],
    index=0
)

# Filter option for pending comments only
show_pending_only = st.checkbox("Show only data without comments", value=False)

# Get data based on filter
if selected_patient == 'all':
    data = get_patient_data_with_comments()
else:
    data = get_patient_data_by_id(selected_patient)

# Filter for pending comments if requested
if show_pending_only:
    data = [item for item in data if item['comment'] is None]

if not data:
    st.info("No data found for the selected criteria.")
    
    # Navigation
    st.divider()
    col1, col2 = st.columns(2)
    if col1.button("← Back to Patient Data"):
        st.switch_page("pages/test_adminPatientData.py")
    if col2.button("← Back to Patient List"):
        st.switch_page("pages/_admin_patient_info.py")
    
    st.stop()

# Format the data for the data editor
formatted_data = []
for item in data:
    # Format timestamps
    created_at = item['created_at']
    comment_date = item['comment_date']
    
    if isinstance(created_at, datetime):
        created_at_str = created_at.strftime("%d-%m-%Y %H:%M")
    else:
        created_at_str = str(created_at) if created_at else "N/A"
    
    if isinstance(comment_date, datetime):
        comment_date_str = comment_date.strftime("%d-%m-%Y %H:%M")
    else:
        comment_date_str = str(comment_date) if comment_date else "N/A"
    
    formatted_data.append({
        "data_id": item['data_id'],
        "patient_id": item['patient_id'],
        "username": item['username'],
        "comment": item['comment'] or "",  # Convert None to empty string for editing
        "data_created_at": created_at_str,
        "comment_date": comment_date_str if item['comment'] else "Not commented yet"
    })

# Convert to DataFrame
df = pd.DataFrame(formatted_data)

# Create a copy of the original data for comparison
if 'original_data' not in st.session_state:
    st.session_state.original_data = df.copy()

# Display the data editor
st.header("Edit Comments")
edited_df = st.data_editor(
    df,
    column_config={
        "data_id": st.column_config.NumberColumn(
            "Data ID",
            help="Unique identifier for the patient data",
            disabled=True,
        ),
        "patient_id": st.column_config.NumberColumn(
            "Patient ID",
            help="Patient identifier",
            disabled=True,
        ),
        "username": st.column_config.TextColumn(
            "Username",
            help="Patient username",
            disabled=True,
        ),
        "comment": st.column_config.TextColumn(
            "Comment",
            help="Comment on patient data",
            width="large",
        ),
        "data_created_at": st.column_config.TextColumn(
            "Data Created At",
            help="When the patient data was created",
            disabled=True,
        ),
        "comment_date": st.column_config.TextColumn(
            "Comment Date",
            help="When the comment was added",
            disabled=True,
        ),
    },
    hide_index=True,
    use_container_width=True,
    num_rows="dynamic"
)

# Check for changes and update the database
if st.button("Save Changes"):
    changes_made = False
    
    # Compare with original data to find changes
    for index, row in edited_df.iterrows():
        original_row = st.session_state.original_data.loc[
            st.session_state.original_data['data_id'] == row['data_id']
        ]
        
        if not original_row.empty and original_row['comment'].values[0] != row['comment']:
            # Comment has changed, update in database
            success = update_comment(row['data_id'], row['patient_id'], row['comment'])
            if success:
                changes_made = True
                st.success(f"Updated comment for Data ID: {row['data_id']}")
    
    if changes_made:
        # Update the session state with the new data
        st.session_state.original_data = edited_df.copy()
        st.rerun()
    else:
        st.info("No changes detected.")

# Pending comments section
with st.expander("Pending Comments Overview"):
    pending_cases = get_pending_comment_cases()
    
    if isinstance(pending_cases, list):
        if pending_cases:
            pending_df = pd.DataFrame(pending_cases, columns=["Data ID", "Patient ID"])
            st.dataframe(pending_df)
        else:
            st.success("No pending comments! All patient data has comments.")
    else:
        st.error(pending_cases)  # Show error message

# Delete comment section
with st.expander("Delete Comments"):
    st.warning("⚠️ Deleting comments is permanent and cannot be undone.")
    
    delete_data_id = st.number_input("Enter Data ID to delete comment", min_value=1, step=1)
    
    if st.button("Delete Comment"):
        # Confirm deletion
        if delete_data_id in df['data_id'].values:
            if st.checkbox("I confirm I want to delete this comment"):
                success = delete_comment(delete_data_id)
                if success:
                    st.success(f"Comment for Data ID {delete_data_id} deleted successfully!")
                    st.rerun()
        else:
            st.error(f"Data ID {delete_data_id} not found.")

# Navigation
st.divider()
col1, col2, col3 = st.columns(3)
if col1.button("← Back to Patient Data"):
    st.switch_page("pages/test_adminPatientData.py")
if col2.button("← Back to Patient List"):
    st.switch_page("pages/_admin_patient_info.py")
if col3.button("← Back to Dashboard"):
    st.switch_page("pages/_admin_dashboard.py")