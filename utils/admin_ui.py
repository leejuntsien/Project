
import streamlit as st

def load_admin_css():
    """Load the shared admin CSS styles"""
    with open("./frontend/static/admin_custom.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def create_toast(message, type="info"):
    """Create a toast notification
    
    Args:
        message (str): The message to display
        type (str): One of "success", "error", "warning", "info"
    """
    toast_classes = {
        "success": "toast toast-success",
        "error": "toast toast-error",
        "warning": "toast toast-warning",
        "info": "toast toast-info"
    }
    
    toast_class = toast_classes.get(type, toast_classes["info"])
    
    st.markdown(
        f"""
        <div class="toast-container">
            <div class="{toast_class}">
                {message}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def format_button(label, key=None, type="primary", on_click=None, disabled=False):
    button_styles = {
        "primary": "background-color: #3b82f6; color: white;",
        "secondary": "background-color: #e5e7eb; color: #374151;",
        "success": "background-color: #10b981; color: white;",
        "danger": "background-color: #ef4444; color: white;",
        "info": "background-color: #3b82f6; color: white;",
    }
    style = button_styles.get(type, button_styles["primary"])
    if disabled:
        style += " opacity: 0.6; pointer-events: none;"

    return st.markdown(
        f"""
        <button style="{style} padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;" 
                {'disabled' if disabled else ''}>
            {label}
        </button>
        """,
        unsafe_allow_html=True,
    )

def dashboard_card(title, content=None):
    """Create a styled dashboard card
    
    Args:
        title (str): Card title
        content (callable): Function that renders the card content
    """
    with st.container():
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown(f"<h3>{title}</h3>", unsafe_allow_html=True)
        if content:
            content()
        st.markdown('</div>', unsafe_allow_html=True)

def create_metric_card(label, value, delta=None, delta_color="normal"):
    """Create a styled metric card
    
    Args:
        label (str): Metric label
        value (str): Metric value
        delta (str, optional): Delta value
        delta_color (str): One of "normal", "good", "bad"
    """
    with st.container():
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(label=label, value=value, delta=delta, delta_color=delta_color)
        st.markdown('</div>', unsafe_allow_html=True)

def patient_card(patient_id, username, data_count, on_click=None):
    """Create a styled patient card
    
    Args:
        patient_id (str): Patient ID
        username (str): Patient username
        data_count (int): Number of data records
        on_click (callable): Function to call when clicked
    """
    with st.container():
        st.markdown(f'''
        <div class="patient-card" onclick="console.log('Card clicked: {patient_id}')">
            <h3>{username}</h3>
            <p>Patient ID: {patient_id}</p>
            <p>Data Records: {data_count}</p>
        </div>
        ''', unsafe_allow_html=True)
        
        if on_click:
            if st.button(f"View {username}", key=f"view_{patient_id}"):
                on_click(patient_id)

def optimize_streamlit():
    """Apply optimizations to reduce full page reruns"""
    # Add these to the session state to track and manage state without triggering reruns
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        
    if 'show_toast' not in st.session_state:
        st.session_state.show_toast = False
        st.session_state.toast_message = ""
        st.session_state.toast_type = "info"
    
    # Display toast message if needed
    if st.session_state.show_toast:
        create_toast(st.session_state.toast_message, st.session_state.toast_type)
        # Reset toast state after displaying
        st.session_state.show_toast = False

def show_toast(message, type="info"):
    """Show a toast message on the next rerun
    
    Args:
        message (str): The message to display
        type (str): One of "success", "error", "warning", "info" 
    """
    st.session_state.show_toast = True
    st.session_state.toast_message = message
    st.session_state.toast_type = type
