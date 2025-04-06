import streamlit as st
from backend_auth import login, register_admin
from utils.security import set_admin_auth

st.set_page_config(page_title="Admin Authentication")

# Clear any existing admin authentication
if not st.session_state.get("admin_authenticated", False):
    set_admin_auth(False)

st.title("Admin Login")

username = st.text_input("Admin Username")
password = st.text_input("Admin Password", type="password")

if st.button("Login"):
    if login("admin_users", username, password):
        set_admin_auth(True, username)
        st.success(f"Welcome, {username}!")
        st.switch_page("pages/_admin_dashboard.py")  # Future admin page
    else:
        st.error("Invalid credentials!")

if st.button("Register New Admin"):
    st.switch_page("pages/_admin_registration.py") #registration page

# Home Button
if st.button("🏠 Home"):
    st.switch_page("main.py")  # Redirect to main.py