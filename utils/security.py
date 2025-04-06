import streamlit as st
import functools
from datetime import datetime, timedelta

def check_session_timeout():
    # Get last activity time
    last_activity = st.session_state.get("last_activity")
    if last_activity:
        # Convert from string back to datetime
        last_activity = datetime.fromisoformat(last_activity)
        # Check if more than 10 minutes have passed
        if datetime.now() - last_activity > timedelta(minutes=10):
            set_admin_auth(False)
            return False
    return True

def update_last_activity():
    # Update last activity time
    st.session_state["last_activity"] = datetime.now().isoformat()

def require_admin_auth(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not is_admin_authenticated() or not check_session_timeout():
            st.error("⚠️ Access Denied: Admin authentication required")
            if not check_session_timeout():
                st.warning("Session expired due to inactivity")
            st.switch_page("pages/admin_auth.py")
            return None
        update_last_activity()
        return func(*args, **kwargs)
    return wrapper

def is_admin_authenticated():
    return st.session_state.get("admin_authenticated", False)

def set_admin_auth(status: bool, username: str = None):
    st.session_state["admin_authenticated"] = status
    if username:
        st.session_state["admin_username"] = username
        update_last_activity()
    elif not status:
        # Clear all admin-related session data
        st.session_state.pop("admin_username", None)
        st.session_state.pop("last_activity", None)
        st.session_state.pop("admin_authenticated", None)
