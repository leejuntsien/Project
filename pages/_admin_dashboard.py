
import streamlit as st
from admin_dashboard_backend import get_pending_comments, get_pending_comment_cases, add_comment, total_count
from utils.security import require_admin_auth, is_admin_authenticated, set_admin_auth
from utils.admin_ui import load_admin_css, create_metric_card, dashboard_card, format_button, show_toast, optimize_streamlit
import math

st.set_page_config(page_title="Admin Dashboard", layout="wide")

# Load custom CSS
load_admin_css()

# Apply optimizations
optimize_streamlit()

# Check authentication before showing any content
if not is_admin_authenticated():
    st.error("⚠️ Access Denied: Admin authentication required")
    st.warning("Please log in to access the admin dashboard.")
    format_button("Go to Login", key="login_redirect", type="primary", on_click=lambda: st.switch_page("pages/_admin_auth.py"))
    st.stop()

# Display admin header with welcome message
st.markdown("""
<div class="admin-header fade-in">
    <h1>🔹 Admin Dashboard</h1>
</div>
""", unsafe_allow_html=True)

st.info(f"Logged in as: {st.session_state.get('admin_username')}")

# Sidebar Navigation with improved styling
with st.sidebar:
    st.header("Navigation")

    # Navigation buttons with icons
    if st.button("📄 User Login Info", key="nav_login_info"):
            st.switch_page("pages/_admin_patient_info.py")

    if st.button("🛢️ User Data", key="nav_user_data"):
             st.switch_page("pages/test_adminPatientData.py")

    if st.button("📊 Data Visualization", key="nav_data_viz"): 
             st.switch_page("pages/Admin_multi_data.py")

    if st.button("💬 Patient Comments", key="nav_patient_comments"): 
             st.switch_page("pages/_admin_patient_comments.py")

    # Logout Button with Confirmation
    if st.button("🚪 Logout"):
                if st.session_state.get("logout_confirmed", False):
                    st.session_state.clear()  # Clears session data
                    st.success("Logged out successfully!")
                    st.switch_page("pages/_admin_auth.py")  # Redirect to login page
                else:
                    st.session_state["logout_confirmed"] = True
                    st.warning("Click Logout again to confirm.")

# **Dashboard Metrics** with better visual styling
st.markdown('<div class="metrics-container fade-in">', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)

with col1:
    create_metric_card("Pending Comments", get_pending_comments())

with col2:
    create_metric_card("Total Patients", total_count())

with col3:
    # Placeholder for additional metrics
    create_metric_card("Active Sessions", "N/A")

with col4:
    # Placeholder for additional metrics
    create_metric_card("System Status", "✅ Online")

st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# **Pending Comments Section** with improved styling
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

    # Initialize session state for view mode
    if 'comment_view' not in st.session_state:
        st.session_state.comment_view = "Scrollable"

    # Radio button for selecting the view mode
    selected_view = st.radio(
        "View Mode", 
        view_options, 
        index=view_options.index(st.session_state.comment_view), 
        horizontal=True
    )
    
    if st.session_state.comment_view == "Scrollable":
        # Create a container for the comments
        comments_container = st.container(height=400)
        
        # Add comments to the container
        with comments_container:
            for data_id, patient_id in pending_cases:
                with st.expander(f"Data ID: {data_id} | Patient: {patient_id}"):
                    comment = st.text_area(f"Add comment for {patient_id} (Data ID {data_id})", key=f"comment_text_{data_id}")

                    if format_button(f"Submit Comment", key=f"comment_{data_id}", type="success"):
                        if comment.strip():
                            add_comment(data_id, patient_id, comment)
                            show_toast("Comment added successfully!", "success")
                            st.rerun()  # Refresh dashboard
                        else:
                            show_toast("Comment cannot be empty!", "warning")
    
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
                    comment = st.text_area(f"Add comment for {patient_id} (Data ID {data_id})", key=f"comment_text_{data_id}")

                    if format_button(f"Submit Comment", key=f"comment_{data_id}", type="success"):
                        if comment.strip():
                            add_comment(data_id, patient_id, comment)
                            show_toast("Comment added successfully!", "success")
                            st.rerun()  # Refresh dashboard
                        else:
                            show_toast("Comment cannot be empty!", "warning")
        
        # Pagination controls
        col1, col2, col3 = st.columns([1, 3, 1])
        page_numbers = list(range(1, total_pages + 1))
        with col1:
            if format_button("◀ Previous", key="prev_page", type="secondary", 
                        disabled=st.session_state.comment_page == 0):
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
            if format_button("Next ▶", key="next_page", type="secondary", 
                        disabled=st.session_state.comment_page >= total_pages - 1):
                st.session_state.comment_page = min(total_pages - 1, st.session_state.comment_page + 1)
                st.rerun()

    # Update session state only if the view changes
    if selected_view != st.session_state.comment_view:
        st.session_state.comment_view = selected_view
        st.session_state.view_changed = True  # Set a flag to trigger rerun
    else:
        st.session_state.view_changed = False

    # Trigger rerun only if the view has changed
    if st.session_state.view_changed:
        st.rerun()

# **Additional Features**
if "refresh_clicked" not in st.session_state:
    st.session_state["refresh_clicked"] = False

st.subheader("🔍 Quick Access")
if st.button ("Refresh Data", key="refresh_btn"):
    st.session_state["refresh_clicked"] = True
    show_toast("Refreshing data...", "info")
    st.rerun()

# Use session state to manage what happens after rerun
if st.session_state["refresh_clicked"]:
    st.write("Data has been refreshed!")
    # Reset the state after handling
    st.session_state["refresh_clicked"] = False
