import streamlit as st
import pandas as pd
from backend_patient_info import get_patient_data, get_patient_summary
from utils.security import is_admin_authenticated

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

for key, default in [
    ('search_patient', ""),  # We'll set this to patient_id later if needed
    ('search_timestamp', ""), 
    ('search_data_id', ""), 
    ('sort_option', "Patient ID"),
    ('current_page', 0),
    ('num_page', 20)
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Initialize session states
if "show_dialog" not in st.session_state:
    st.session_state.show_dialog = False
if "show_delete_dialog"not in st.session_state:
    st.session_state.show_delete_dialog = False
if "data_id" not in st.session_state:
    st.session_state.data_id = None

@st.dialog(f"Confirm Navigation")
def dialog_data_id(data_id, patient_id):
    
    col1, col2 = st.columns(2)
    if st.session_state.show_dialog:
        st.write(f"Confirm switch page to {data_id}'s data?")
        st.query_params["id"] = data_id
        st.session_state.data_id = data_id
        with col1:
            if st.button("✅ Confirm"):
                st.query_params["id"] = data_id
                st.session_state.data_id = data_id
                st.session_state.show_dialog = False
                st.switch_page("pages/_admin_data_instance.py")
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.show_dialog = False
                st.rerun()
    elif st.session_state.show_delete_dialog:
        st.write(f"Confirm deletion of Patient {patient_id}'s {data_id} data?")
        st.warning("This action cannot be undone!")
        with col1:
            if st.button("✅ Confirm"):
                # Call the delete function
                if delete_data(data_id):
                    # If deletion was successful
                    st.session_state.show_delete_dialog = False
                    st.rerun()  # Refresh the page to show updated data
            else:
                # If button not clicked, keep dialog open
                pass
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.show_delete_dialog = False
                st.rerun()

    

def delete_data(data_id):
    """
    Delete patient data by data_id from PostgreSQL database
    
    Args:
        data_id (str): The ID of the data to delete
    
    Returns:
        bool: True if deletion was successful, False otherwise
    """
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
    patient_id = str(st.session_state.get("patient_id"))
    st.session_state.search_patient =patient_id
     
else:
    patient_id = st.session_state.search_patient
    st.session_state.patient_id = ""

# Debugging: Check if patient_id is captured
st.markdown(f"<h1 style='text-align: center;'>🔍 Captured patient_id: {patient_id}</h1>", unsafe_allow_html=True)

# Now set search_patient to patient_id if needed
#if not st.session_state.search_patient:
#    patient_id=st.session_state.search_patient 

# Initialize session state variables
for key, default in [
    ('search_patient', patient_id if patient_id else ""),  # ✅ Default to patient_id from URL
    ('search_timestamp', ""), 
    ('search_data_id', ""), 
    ('sort_option', 0),
    ('current_page', 0),
    ('num_page', 20)
]:
    if key not in st.session_state:
        st.session_state[key] = default

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
    sort_option = st.selectbox("🔽 Sort By", ["Patient ID", "Data ID", "Timestamp"], index=["Patient ID", "Data ID", "Timestamp"].index(st.session_state.sort_option))

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

if 'selected_view' in st.session_state:
    if st.session_state.selected_view == "Scrollable"and st.session_state.num_page != len(filtered_df):
         st.session_state.num_page = len(filtered_df)
         st.session_state.current_page = 0
         st.rerun()
    elif st.session_state.selected_view == "Pagination(20)" and st.session_state.num_page != 20:
        st.session_state.num_page = 20
        st.rerun()
    elif st.session_state.selected_view == "Pagination(50)" and st.session_state.num_page != 50:
        st.session_state.num_page = 50
        st.rerun()

# ✅ Pagination
rows_per_page = st.session_state.get("num_page") | st.session_state.num_page
total_pages = max(1, (len(filtered_df) + rows_per_page - 1) // rows_per_page)

# Ensure current page is valid
if st.session_state.current_page >= total_pages:
    st.session_state.current_page = 0

# Get current page's data
start_idx = st.session_state.current_page * rows_per_page
end_idx = min(start_idx + rows_per_page, len(filtered_df))
page_df = filtered_df.iloc[start_idx:end_idx]

page_df = page_df.reset_index(drop=True)
page_df['Index'] = range(start_idx + 1, end_idx + 1)

with col1:
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
    </style>
    """,
    unsafe_allow_html=True
)

def create_action_buttons(row):
    data_id = row['data_id']
    patient_id = row['patient_id']
    
    # Create a unique key for each selectbox
    select_key = f"action_select_{data_id}"
    
    # Create selectbox
    option = st.selectbox("Choose action", 
                         options=["Select Action", "View Data", "Delete Data"],
                         key=select_key)

    # Handle the selected option
    if option == "View Data":
        st.session_state.selected_data_id = data_id
        st.session_state.show_view_dialog = True
        st.session_state.dialog_data_id = data_id
        return "View Data"
    elif option == "Delete Data":
        st.session_state.selected_data_id = data_id
        st.session_state.show_delete_dialog = True
        st.session_state.dialog_data_id = data_id
        st.session_state.dialog_patient_id = patient_id
        return "Delete Data"
    else:
        return "Select Action"
        

    

# Add index column
filtered_df = filtered_df.reset_index(drop=True)
filtered_df['#'] = range(1, len(filtered_df) + 1)


# Add actions column
filtered_df['actions'] = filtered_df.apply(create_action_buttons, axis=1)

# Reorder columns
display_df = filtered_df[['#', 'patient_id', 'data_id', 'created_at', 'actions']]

# ✅ Display data based on view mode
if st.session_state.selected_view == "Scrollable":
    # Display the full dataframe in scrollable mode
    st.dataframe(
        display_df,
        column_config={
            "#": st.column_config.NumberColumn(width="small"),
            "patient_id": st.column_config.TextColumn(
                "Patient ID", 
                help="Patient identifier",
                width="medium"
            ),
            "data_id": st.column_config.TextColumn(
                "Data ID",
                help="Data identifier",
                width="medium"
            ),
            "created_at": st.column_config.DatetimeColumn(
                "Created At",
                format="YYYY-MM-DD HH:mm:ss",
                width="medium"
            ),
            "actions": st.column_config.Column(
                "Actions",
                width="medium",
                help="View or delete data"
            )
        },
        hide_index=True,
        height=400
    )
else:
    # Pagination mode
    rows_per_page = st.session_state.num_page
    total_pages = max(1, (len(filtered_df) + rows_per_page - 1) // rows_per_page)
    
    # Ensure current page is valid
    if st.session_state.current_page >= total_pages:
        st.session_state.current_page = 0
    
    # Get current page's data
    start_idx = st.session_state.current_page * rows_per_page
    end_idx = min(start_idx + rows_per_page, len(filtered_df))
    page_df = display_df.iloc[start_idx:end_idx]
    
    # Display the current page
    st.dataframe(
        page_df,
        column_config={
            "#": st.column_config.NumberColumn(width="small"),
            "patient_id": st.column_config.TextColumn(
                "Patient ID", 
                help="Patient identifier",
                width="medium"
            ),
            "data_id": st.column_config.TextColumn(
                "Data ID",
                help="Data identifier",
                width="medium"
            ),
            "created_at": st.column_config.DatetimeColumn(
                "Created At",
                format="YYYY-MM-DD HH:mm:ss",
                width="medium"
            ),
            "actions": st.column_config.Column(
                "Actions",
                width="medium",
                help="View or delete data"
            )
        },
        hide_index=True,
        height=400
    )   
        
        
            
    

    # Generate the list of page numbers
    page_numbers = list(range(1, total_pages + 1))
    # Pagination controls
    st.markdown('<div class="pagination">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 4, 2])
    
    with col1:
        if st.button("◀ Previous", disabled=st.session_state.current_page == 0):
            st.session_state.current_page = max(0, st.session_state.current_page - 1)
            st.rerun()
            

    # Page Info and Page Selector
    with col2:
        st.markdown(f"<div style='text-align: center;'>Page {st.session_state.current_page + 1} of {total_pages} ({start_idx + 1}-{end_idx} of {len(filtered_df)})</div>", unsafe_allow_html=True)
        
        # Scrollable selectbox for selecting the page number
        selected_page = st.selectbox("",key= page_numbers, index=st.session_state.current_page)

        # Update the current page based on the selection
        if selected_page != st.session_state.current_page + 1:
            st.session_state.current_page = selected_page - 1
            st.rerun()

            
    with col3:
        if st.button("Next ▶", disabled=st.session_state.current_page >= total_pages - 1):
            st.session_state.current_page = min(total_pages - 1, st.session_state.current_page + 1)
            st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)



# ✅ Table View Options - KEPT AT THE BOTTOM FOR UI
table_view_options = ["Scrollable", "Pagination(20)", "Pagination(50)"]
# Determine the default index based on current num_page value
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

# ✅ Navigation Buttons (outside the table area)
st.write("---")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏠 Back to Patient List",key="back_main"):
        st.switch_page("pages/_admin_patient_info.py")
        
with col2:
    if st.button("🔄 Refresh Data", key ="refresh_main"):
        st.rerun()
        
# Then, update your "Show All Data" button at the bottom:
if col3.button("🔙 Show All Data"):
    # Set the clear_filters parameter to true
    st.query_params["clear_filters"] = "true"
    st.rerun()


# Handle confirmation dialog
if st.session_state.show_view_dialog:
    dialog_data_id(data_id = st.session_state.dialog_data_id, patient_id=st.session_state.dialog_patient_id)

st.sidebar.title("Navigaion")
if st.sidebar.button("🔙 Show All Data", key = "refresh_sidebar"):
    # Set the clear_filters parameter to true
    st.query_params["clear_filters"] = "true"
    st.rerun()
if st.sidebar.button("🏠 Back to Patient List",key="back_main"):
    st.switch_page("pages/_admin_patient_info.py")
       
 