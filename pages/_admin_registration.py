import streamlit as st
from backend_auth import login, register_admin
from utils.security import require_admin_auth, is_admin_authenticated, set_admin_auth

st.set_page_config(page_title="Admin Registration", layout="centered")

if not is_admin_authenticated():
    st.title("⚠️ Admin Authentication Required")
    st.warning("You must be logged in as an admin to access this page.")
    
    auth_username = st.text_input("Admin Username")
    auth_password = st.text_input("Admin Password", type="password")

    if st.button("Login"):
        if login("admin_users", auth_username, auth_password):
            set_admin_auth(True, auth_username)
            st.success("Authentication successful!")
            st.rerun()
        else:
            st.error("Authentication failed. Only registered admins can access this page.")

    if st.button("Back to Login"):
        st.switch_page("pages/_admin_auth.py")
else:
    st.title("Register a New Admin")
    st.info(f"Logged in as: {st.session_state.get('admin_username')}")

    new_username = st.text_input("New Admin Username")
    new_password = st.text_input("New Admin Password", type="password")

    if st.button("Register New Admin"):
        if new_username and new_password:
            message = register_admin(st.session_state["admin_username"], new_username, new_password)
            st.success(message)
            st.switch_page("pages/_admin_auth.py")
        else:
            st.error("Please fill in all fields")

    # Logout option
    if st.button("Logout"):
        set_admin_auth(False)
        st.success("Logged out successfully!")
        st.switch_page("pages/_admin_auth.py")

    # Home Button
    if st.button("🏠 Home"):
        st.switch_page("main.py")