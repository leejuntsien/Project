import streamlit as st
import pandas as pd
from backend_patient_info import get_patient_data, get_patient_summary
from utils.security import is_admin_authenticated
import numpy as np

st.set_page_config(page_title="Patient Data", layout="wide")

# ✅ Authentication Check
if not is_admin_authenticated():
    st.error("⚠️ Access Denied: Admin authentication required")
    st.warning("Please log in to access patient data.")
    if st.button("Go to Login"):
        st.switch_page("pages/_admin_auth.py")
    st.stop()

# Check for clear_filters parameter
clear_filters = st.query_params.get("clear_filters", "false") == "true"

# If clear_filters is true, reset all filter-related session state variables
if clear_filters:
    # Reset filter-related session state variables
    st.session_state.search_patient = ""
    st.session_state.patient_id=""
    st.session_state.search_timestamp = ""
    st.session_state.search_data_id = ""
    st.session_state.sort_option = "Patient ID"
    # Remove the clear_filters parameter
    st.query_params.clear()

# Initialize session state variables
for key, default in [
    ('search_patient', ""),
    ('search_timestamp', ""), 
    ('search_data_id', ""), 
    ('sort_option', "Patient ID"),
    ('current_page', 0),
    ('num_page', 20),
    ('selected_rows', {}),  # Dictionary to store selected rows
    ('options', "Select_Action"),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Initialize dialog state variables
if "show_dialog" not in st.session_state:
    st.session_state.show_dialog = False
if "show_delete_dialog" not in st.session_state:
    st.session_state.show_delete_dialog = False
if "data_id" not in st.session_state:
    st.session_state.data_id = None
if "dialog_data_id" not in st.session_state:
    st.session_state.dialog_data_id = None
if "dialog_patient_id" not in st.session_state:
    st.session_state.dialog_patient_id = None
# Initialize bulk delete state variables
if "is_bulk_delete" not in st.session_state:
    st.session_state.is_bulk_delete = False
if "bulk_delete_ids" not in st.session_state:
    st.session_state.bulk_delete_ids = []
# Initialize multiple delete state variables
if "show_multiple_delete_confirm" not in st.session_state:
    st.session_state.show_multiple_delete_confirm = False
if "multiple_data_ids" not in st.session_state:
    st.session_state.multiple_data_ids = []

def delete_data(data_id):
    """
    Delete patient data by data_id from PostgreSQL database
    
    Args:
        data_id (str): The ID of the data to delete
    
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    data_id=str(data_id)
    try:
        import psycopg2
        from psycopg2 import sql
        from backend_auth import get_db_connection
        
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # SQL query to delete the data
        delete_query = sql.SQL("""
            DELETE FROM patient_data 
            WHERE data_id = %s
            RETURNING data_id
        """)
        
        # Execute the query
        cursor.execute(delete_query, (data_id,))
        
        # Check if a row was deleted
        deleted_row = cursor.fetchone()
        
        # Commit the transaction
        conn.commit()
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        
        if deleted_row:
            st.success(f"Data ID {data_id} has been successfully deleted.")
            return True
        else:
            st.warning(f"No data found with ID {data_id}.")
            return False
            
    except Exception as e:
        st.error(f"An error occurred while deleting Data ID {data_id}: {str(e)}")
        # If there's an error, try to rollback the transaction
        try:
            if conn:
                conn.rollback()
        except:
            pass
        return False

# ✅ Get patient ID from URL (if provided)
if st.session_state.search_patient == "":
    patient_id = str(st.session_state.get("patient_id", ""))
    st.session_state.search_patient = patient_id
else:
    patient_id = st.session_state.search_patient
    st.session_state.patient_id = ""

# Debugging: Check if patient_id is captured
st.markdown(f"<h1 style='text-align: center;'>🔍 Captured patient_id: {patient_id}</h1>", unsafe_allow_html=True)

# ✅ Fetch patient data
patient_data = get_patient_data()  # Returns all data if no ID
df = pd.DataFrame(patient_data, columns=["patient_id", "data_id", "created_at", "num_instances"])

# ✅ Fetch patient summary info for tooltips
patient_summary = get_patient_summary()  # {patient_id: (username, total_trials, latest_timestamp)}

# ✅ Filters (Searchbars)
st.markdown("<h3 style='text-align: center;'>Search & Filter</h3>", unsafe_allow_html=True)

# Define columns for search inputs
col1, col2, col3, col4 = st.columns(4)
with col1:
    search_patient = st.text_input("🔍 Search by Patient ID / Username", key="search_patient")
with col2:
    search_timestamp = st.text_input("📅 Search by Timestamp/Date", key="search_timestamp")
with col3:
    search_data_id = st.text_input("📂 Search by Data ID", key="search_data_id")
with col4:
    sort_options = ["Patient ID", "Data ID", "Timestamp"]
    sort_option = st.selectbox("🔽 Sort By", sort_options, index=sort_options.index(st.session_state.sort_option))
    st.session_state.sort_option = sort_option

# ✅ Apply Filters
filtered_df = df.copy()
if st.session_state.search_patient:
    filtered_df = filtered_df[filtered_df["patient_id"].astype(str).str.contains(st.session_state.search_patient, case=False)]
if st.session_state.search_timestamp:
    filtered_df = filtered_df[filtered_df["created_at"].astype(str).str.contains(st.session_state.search_timestamp, case=False)]
if st.session_state.search_data_id:
    filtered_df = filtered_df[filtered_df["data_id"].astype(str).str.contains(st.session_state.search_data_id, case=False)]

# ✅ Sorting
sort_column_map = {"Patient ID": "patient_id", "Data ID": "data_id", "Timestamp": "created_at"}
filtered_df = filtered_df.sort_values(by=sort_column_map[st.session_state.sort_option])

# Update view mode based on selected_view
if 'selected_view' in st.session_state:
    if st.session_state.selected_view == "Scrollable":
        st.session_state.num_page = len(filtered_df)
    elif st.session_state.selected_view == "Pagination(20)":
        st.session_state.num_page = 20
    elif st.session_state.selected_view == "Pagination(50)":
        st.session_state.num_page = 50

# ✅ Pagination - Fix the bitwise OR issue
rows_per_page = st.session_state.num_page  # Use the session state value directly
total_pages = max(1, (len(filtered_df) + rows_per_page - 1) // rows_per_page)

# Ensure current page is valid
if st.session_state.current_page >= total_pages:
    st.session_state.current_page = 0

# Get current page's data
start_idx = st.session_state.current_page * rows_per_page
end_idx = min(start_idx + rows_per_page, len(filtered_df))
page_df = filtered_df.iloc[start_idx:end_idx]

# Add index column
page_df = page_df.reset_index(drop=True)
page_df['Index'] = range(start_idx + 1, end_idx + 1)
page_df['Select'] = np.zeros(len(page_df), dtype=bool)
page_df['Action'] = 'Select Action' * len(page_df)
# Display total records
st.markdown(f"<h3 style='text-align: center;'>Total Records: {len(filtered_df)}</h3>", unsafe_allow_html=True)

# ✅ Custom CSS for buttons
st.markdown(
    """
    <style>
    /* Button styling */
    .stButton > button {
        border-radius: 4px;
        padding: 0.25rem 0.5rem;
        font-size: 0.8rem;
    }
    
    /* View button */
    .view-button button {
        background-color: #3498db;
        color: white;
    }
    
    /* Delete button */
    .delete-button button {
        background-color: #e74c3c;
        color: white;
    }
    
    /* Center text in dataframe */
    [data-testid="stDataFrame"] table {
        text-align: center !important;
    }
    
    /* Center column headers */
    [data-testid="stDataFrame"] th {
        text-align: center !important;
    }
    
    /* Center pagination controls */
    .pagination {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 1rem 0;
    }
    
    .pagination button {
        margin: 0 0.5rem;
    }
    
    /* Action buttons container */
    .action-buttons {
        display: flex;
        justify-content: center;
        gap: 1rem;
        margin: 1rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Function to handle row selection
def handle_selection(data_id, selected):
    if selected:
        st.session_state.selected_rows[data_id] = True
    else:
        if data_id in st.session_state.selected_rows:
            del st.session_state.selected_rows[data_id]

# Add selection column to the dataframe
def add_selection_column(row):
    data_id = row['data_id']
    is_selected = st.session_state.selected_rows.get(data_id, False)
    checkbox_key = f"select_{data_id}"
    
    # Create a checkbox for selection
    selected = st.checkbox("", value=is_selected, key=checkbox_key)
    
    # Update selection state
    handle_selection(data_id, selected)
    
    return selected

# First, initialize a variable to store the selected action
if 'selected_action' not in st.session_state:
    st.session_state.selected_action = None

# Function to handle selection changes
def handle_selection_change(edited_rows):
    for idx, changes in edited_rows.items():
        if 'Select' in changes:
            row_idx = int(idx)
            data_id = page_df.iloc[row_idx]['data_id']
            is_selected = changes['Select']
            handle_selection(data_id, is_selected)

# Function to handle action changes
def handle_action_change(edited_rows):
    for idx, changes in edited_rows.items():
        if 'Action' in changes and changes['Action'] != 'Select_Action':
            row_idx = int(idx)
            data_id = page_df.iloc[row_idx]['data_id']
            patient_id = page_df.iloc[row_idx]['patient_id']
            action = changes['Action']
            
            # Store the selected action and related info
            st.session_state.selected_action = action
            st.session_state.selected_data_id = data_id
            st.session_state.selected_patient_id = patient_id
            
            # Return early to trigger rerun
            return True
    
    return False

# Use the data editor with proper callbacks
edited_df = st.data_editor(
    page_df[['Index', 'Select', 'patient_id', 'data_id', 'created_at']],
    column_config={
        "Select": st.column_config.CheckboxColumn(
            "Select",
            help="Select this row",
            width="small",
            default=False
        )
    },
    disabled=[],
    hide_index=True,
    key="patient_data_editor"
)

# Process the edited data
if st.session_state.get("patient_data_editor") is not None:
    edited_data = st.session_state["patient_data_editor"]
    
    # Handle checkbox selections
    if "edited_rows" in edited_data and edited_data["edited_rows"]:
        handle_selection_change(edited_data["edited_rows"])
    
    # Handle action selections
    if "edited_rows" in edited_data and edited_data["edited_rows"]:
        if handle_action_change(edited_data["edited_rows"]):
            # Process the selected action
            action = st.session_state.selected_action
            data_id = st.session_state.selected_data_id
            patient_id = st.session_state.selected_patient_id
            
            if action == "View":
                # Set up for view dialog
                st.session_state.dialog_data_id = data_id
                st.session_state.dialog_patient_id = patient_id
                st.session_state.show_dialog = True
                st.rerun()
            elif action == "Delete":
                # Set up for delete dialog
                st.session_state.dialog_data_id = data_id
                st.session_state.dialog_patient_id = patient_id
                st.session_state.show_delete_dialog = True
                st.rerun()
col1, col2 = st.columns(2)

with col1:
    if st.button("View Selected Data", disabled=len(st.session_state.selected_rows) != 1):
        # Get the selected data_id (there should be only one)
        selected_data_id = list(st.session_state.selected_rows.keys())[0]
        
        # Get the patient_id for this data_id
        selected_row = filtered_df[filtered_df['data_id'] == selected_data_id]
        if not selected_row.empty:
            selected_patient_id = selected_row.iloc[0]['patient_id']
            
            # Show confirmation dialog
            st.session_state.dialog_data_id = str(selected_data_id)
            st.session_state.dialog_patient_id = str(selected_patient_id)
            st.session_state.show_dialog = True
            st.rerun()
        else:
            st.error("Selected data not found.")

# In the Delete Selected Data button section:
with col2:
    if st.button("Delete Selected Data", disabled=len(st.session_state.selected_rows) == 0):
        # Get all selected data_ids
        selected_data_ids = list(st.session_state.selected_rows.keys())
        
        # Show confirmation dialog for deletion
        if len(selected_data_ids) == 1:
            # Single deletion - use the existing dialog
            selected_data_id = str(selected_data_ids[0])
            selected_row = filtered_df[filtered_df['data_id'].astype(str) == selected_data_id]
            if not selected_row.empty:
                selected_patient_id = str(selected_row.iloc[0]['patient_id'])
                
                # Show confirmation dialog
                st.session_state.dialog_data_id = selected_data_id
                st.session_state.dialog_patient_id = selected_patient_id
                st.session_state.show_delete_dialog = True
                st.rerun()
        else:
            # Multiple deletion - show confirmation button first
            st.session_state.show_multiple_delete_confirm = True
            st.session_state.multiple_data_ids = selected_data_ids
            st.rerun()

# Add this section after the Delete Selected Data button
if st.session_state.show_multiple_delete_confirm:
    st.warning(f"Are you sure you want to delete {len(st.session_state.multiple_data_ids)} selected items?")
    
    if st.button("Confirm Multiple Deletion"):
        # Set up the dialog for the first item in the list
        if st.session_state.multiple_data_ids:
            # Store all IDs in a special session state variable
            st.session_state.bulk_delete_ids = st.session_state.multiple_data_ids
            
            # Set a flag to indicate we're doing bulk deletion
            st.session_state.is_bulk_delete = True
            
            # Set up the dialog with the first ID (just as a placeholder)
            first_id = str(st.session_state.multiple_data_ids[0])
            st.session_state.dialog_data_id = "multiple"
            st.session_state.dialog_patient_id = "multiple"
            st.session_state.show_delete_dialog = True
            
            # Clear the confirmation state
            st.session_state.show_multiple_delete_confirm = False
            
            st.rerun()
    
    if st.button("Cancel"):
        st.session_state.show_multiple_delete_confirm = False
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# Pagination controls (only for pagination modes)
if st.session_state.get('selected_view', 'Scrollable') != "Scrollable":
    st.markdown('<div class="pagination">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 4, 2])
    
    with col1:
        if st.button("◀ Previous", disabled=st.session_state.current_page == 0):
            st.session_state.current_page = max(0, st.session_state.current_page - 1)
            st.rerun()
    
    with col2:
        st.markdown(f"<div style='text-align: center;'>Page {st.session_state.current_page + 1} of {total_pages} ({start_idx + 1}-{end_idx} of {len(filtered_df)})</div>", unsafe_allow_html=True)
        
        # Scrollable selectbox for selecting the page number
        page_numbers = list(range(1, total_pages + 1))
        selected_page = st.selectbox("", page_numbers, index=st.session_state.current_page)
        
        # Update the current page based on the selection
        if selected_page != st.session_state.current_page + 1:
            st.session_state.current_page = selected_page - 1
            st.rerun()
    
    with col3:
        if st.button("Next ▶", disabled=st.session_state.current_page >= total_pages - 1):
            st.session_state.current_page = min(total_pages - 1, st.session_state.current_page + 1)
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# ✅ Table View Options
table_view_options = ["Scrollable", "Pagination(20)", "Pagination(50)"]
# Determine the default index based on current view_mode
default_index = 0
if st.session_state.num_page == 20:
    default_index = 1
elif st.session_state.num_page == 50:
    default_index = 2

# Use a callback to handle the selection
def on_view_change():
    st.session_state.selected_view = st.session_state.view_selector
    st.rerun()

# Display the selectbox with the callback
st.markdown("<div style='text-align: center; font-size: 18px; font-weight: bold;'>Table View</div>", unsafe_allow_html=True)
selected_view = st.selectbox(
    "", 
    table_view_options, 
    index=default_index,
    key="view_selector",
    on_change=on_view_change
)

# ✅ Navigation Buttons
st.write("---")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏠 Back to Patient List"):
        st.switch_page("pages/_admin_patient_info.py")
        
with col2:
    if st.button("🔄 Refresh Data"):
        st.session_state.selected_rows = {}  # Clear selections
        st.rerun()
        
with col3:
    if st.button("🔙 Show All Data"):
        # Set the clear_filters parameter to true
        st.query_params["clear_filters"] = "true"
        st.session_state.selected_rows = {}  # Clear selections
        st.rerun()

@st.dialog("Confirm Action") 
def dialog_data_id():
    if st.session_state.show_dialog or st.session_state.show_delete_dialog:
        data_id = st.session_state.dialog_data_id

        col1, col2 = st.columns(2)

        if st.session_state.show_dialog:
            st.write(f"Confirm switch page to {data_id}'s data?")
            with col1:
                if st.button("✅ Confirm", key="confirm_dialog"):
                    st.query_params["data_id"] = str(data_id)
                    st.session_state.data_id = data_id
                    st.session_state.show_dialog = False
                    st.switch_page("pages/_admin_data_instance.py")
            with col2:
                if st.button("❌ Cancel", key="cancel_dialog"):
                    st.session_state.show_dialog = False
                    st.rerun()

        elif st.session_state.show_delete_dialog:
            patient_id = st.session_state.dialog_patient_id
            
            # Check if this is a bulk delete operation
            if st.session_state.is_bulk_delete:
                st.warning(f"Are you sure you want to delete {len(st.session_state.bulk_delete_ids)} selected items?")
                st.write("This action cannot be undone.")
                
                with col1:
                    if st.button("✅ Delete All", key="confirm_bulk_delete_dialog"):
                        # Process all IDs in the bulk delete list
                        success_count = 0
                        for delete_id in st.session_state.bulk_delete_ids:
                            delete_id = str(delete_id)
                            if delete_data(delete_id):
                                success_count += 1
                                # Remove from selected rows if present
                                if delete_id in st.session_state.selected_rows:
                                    del st.session_state.selected_rows[delete_id]
                        
                        # Show success message
                        st.success(f"Successfully deleted {success_count} out of {len(st.session_state.bulk_delete_ids)} items.")
                        
                        # Reset bulk delete state
                        st.session_state.is_bulk_delete = False
                        st.session_state.bulk_delete_ids = []
                        st.session_state.show_delete_dialog = False
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel", key="cancel_bulk_delete_dialog"):
                        # Reset bulk delete state
                        st.session_state.is_bulk_delete = False
                        st.session_state.bulk_delete_ids = []
                        st.session_state.show_delete_dialog = False
                        st.rerun()
            else:
                # Regular single item delete
                st.warning(f"Are you sure you want to delete Data ID: {data_id} for Patient: {patient_id}?")
                st.write("This action cannot be undone.")

                with col1:
                    if st.button("✅ Delete", key="confirm_delete_dialog"):
                        # Call the delete function
                        if delete_data(data_id):
                            st.session_state.show_delete_dialog = False
                            if data_id in st.session_state.selected_rows:
                                del st.session_state.selected_rows[data_id]
                            st.rerun()
                with col2:
                    if st.button("❌ Cancel", key="cancel_delete_dialog"):
                        st.session_state.show_delete_dialog = False
                        st.rerun()

if st.session_state.show_dialog or st.session_state.show_delete_dialog:
    dialog_data_id()
# Sidebar navigation
st.sidebar.title("Navigation")
if st.sidebar.button("🔙 Show All Data", key="sidebar_show_all"):
    # Set the clear_filters parameter to true
    st.query_params["clear_filters"] = "true"
    st.session_state.selected_rows = {}  # Clear selections
    st.rerun()
if st.sidebar.button("🏠 Back to Patient List", key="sidebar_back"):
    st.switch_page("pages/_admin_patient_info.py")