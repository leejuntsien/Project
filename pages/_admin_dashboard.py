import streamlit as st
from admin_dashboard_backend import get_pending_comments, get_pending_comment_cases, add_comment, total_count
from utils.security import require_admin_auth, is_admin_authenticated, set_admin_auth
import math

st.set_page_config(page_title="Admin Dashboard", layout="wide")

# Check authentication before showing any content
if not is_admin_authenticated():
    st.error("⚠️ Access Denied: Admin authentication required")
    st.warning("Please log in to access the admin dashboard.")
    if st.button("Go to Login"):
        st.switch_page("pages/_admin_auth.py")
    st.stop()

st.title("🔹 Admin Dashboard")
st.info(f"Logged in as: {st.session_state.get('admin_username')}")

# Sidebar Navigation
with st.sidebar:
    st.header("Navigation")

    if st.button("📄 User Login Info"):
        st.switch_page("pages/_admin_patient_info.py")

    if st.button("🛢️ User Data"):
        st.switch_page("pages/test_adminPatientData.py")

    if st.button("📊 Data Visualization"):
        st.switch_page("pages/Admin_multi_data.py")

    if st.button("💬 Patient Comments"):
        st.switch_page("pages/_admin_patient_comments.py")

    # Logout Button with Confirmation
    if st.button("🚪 Logout"):
        if st.session_state.get("logout_confirmed", False):
            st.session_state.clear()  # Clears session data
            st.success("Logged out successfully!")
            st.switch_page("main.py")  # Redirect to login page
        else:
            st.session_state["logout_confirmed"] = True
            st.warning("Click Logout again to confirm.")

# **Dashboard Metrics**
col1, col2 = st.columns(2)

with col1:
    st.metric(label="Pending Comments", value=get_pending_comments())

with col2:
    st.metric(label="Total Patients", value=total_count())

st.divider()

# **Pending Comments Section**
st.subheader("📝 Pending Comments")

# Add CSS for scrollable container
st.markdown("""
<style>
.comments-container {
    max-height: 400px;
    overflow-y: auto;
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 10px;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

pending_cases = get_pending_comment_cases()

if not pending_cases:
    st.success("All data entries have comments! ✅")
else:
    # Add view options
    view_options = ["Scrollable", "Paginated"]
    if 'comment_view' not in st.session_state:
        st.session_state.comment_view = "Scrollable"
    
    selected_view = st.radio("View Mode", view_options, index=view_options.index(st.session_state.comment_view), horizontal=True)
    
    if selected_view != st.session_state.comment_view:
        st.session_state.comment_view = selected_view
        st.rerun()
    
    if st.session_state.comment_view == "Scrollable":
        # Start scrollable container
        #st.markdown('<div class="comments-container">', unsafe_allow_html=True)
        
        # Create a container for the comments
        comments_container = st.container(height=400)
        
        # Add comments to the container
        with comments_container:
            for data_id, patient_id in pending_cases:
                with st.expander(f"Data ID: {data_id} | Patient: {patient_id}"):
                    comment = st.text_area(f"Add comment for {patient_id} (Data ID {data_id})")

                    if st.button(f"Submit Comment for {patient_id}", key=f"comment_{data_id}"):
                        if comment.strip():
                            add_comment(data_id, patient_id, comment)
                            st.success("Comment added!")
                            st.rerun()  # Refresh dashboard
                        else:
                            st.warning("Comment cannot be empty!")
        
        # End scrollable container
        st.markdown('</div>', unsafe_allow_html=True)
    
    else:  # Paginated view
        # Initialize pagination state
        if 'comment_page' not in st.session_state:
            st.session_state.comment_page = 0
        
        # Set items per page
        items_per_page = 10
        total_pages = math.ceil(len(pending_cases) / items_per_page)
        
        # Calculate start and end indices for current page
        start_idx = st.session_state.comment_page * items_per_page
        end_idx = min(start_idx + items_per_page, len(pending_cases))
        
        # Display current page items
        current_page_cases = pending_cases[start_idx:end_idx]
        
        # Create a container for the comments
        comments_container = st.container()
        
        # Add comments to the container
        with comments_container:
            for data_id, patient_id in current_page_cases:
                with st.expander(f"Data ID: {data_id} | Patient: {patient_id}"):
                    comment = st.text_area(f"Add comment for {patient_id} (Data ID {data_id})")

                    if st.button(f"Submit Comment for {patient_id}", key=f"comment_{data_id}"):
                        if comment.strip():
                            add_comment(data_id, patient_id, comment)
                            st.success("Comment added!")
                            st.rerun()  # Refresh dashboard
                        else:
                            st.warning("Comment cannot be empty!")
        
        # Pagination controls
        col1, col2, col3 = st.columns([1, 3, 1])
        page_numbers = list(range(1, total_pages + 1))
        with col1:
            if st.button("◀ Previous", disabled=st.session_state.comment_page == 0):
                st.session_state.comment_page = max(0, st.session_state.comment_page - 1)
                st.rerun()
        
        with col2:
            st.markdown(f"<div style='text-align: center;'>Page {st.session_state.comment_page + 1} of {total_pages}</div>", unsafe_allow_html=True)
            # Scrollable selectbox for selecting the page number
            selected_page = st.selectbox("", page_numbers, index=st.session_state.comment_page)

            # Update the current page based on the selection
            if selected_page != st.session_state.comment_page + 1:
                st.session_state.comment_page = selected_page - 1
                st.rerun()

        
        with col3:
            if st.button("Next ▶", disabled=st.session_state.comment_page >= total_pages - 1):
                st.session_state.comment_page = min(total_pages - 1, st.session_state.comment_page + 1)
                st.rerun()

# **Additional Features**
if "refresh_clicked" not in st.session_state:
    st.session_state["refresh_clicked"] = False

st.subheader("🔍 Quick Access")

# add searchbar for quick access of data

if st.button("Refresh Data"):
    st.session_state["refresh_clicked"] = True
    st.rerun()

# Use session state to manage what happens after rerun
if st.session_state["refresh_clicked"]:
    st.write("Data has been refreshed!")
    # Reset the state after handling
    st.session_state["refresh_clicked"] = False