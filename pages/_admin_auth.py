
import streamlit as st
from backend_auth import login, register_admin
from utils.security import set_admin_auth

# Page configuration
st.set_page_config(page_title="Admin Authentication", layout="wide")

# Apply custom CSS
with open("frontend/static/enhanced_style.css", "r") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Add a subtle background pattern
st.markdown("""
<style>
body {
    background-image: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    background-attachment: fixed;
    background-size: cover;
}
.login-container {
    max-width: 450px;
    margin: 2rem auto;
    padding: 2rem;
    background: white;
    border-radius: 10px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}
.login-header {
    text-align: center;
    margin-bottom: 2rem;
}
.login-header h1 {
    color: #2c3e50;
    margin-bottom: 0.5rem;
}
.login-header p {
    color: #7f8c8d;
    font-size: 0.9rem;
}
.form-group {
    margin-bottom: 1.5rem;
}
.form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #34495e;
}
.form-control {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    font-size: 1rem;
}
.btn-primary {
    background-color: #3498db;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 0.75rem 1rem;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    width: 100%;
    transition: background-color 0.3s ease;
}
.btn-primary:hover {
    background-color: #2980b9;
}
.login-footer {
    text-align: center;
    margin-top: 1.5rem;
    font-size: 0.9rem;
    color: #7f8c8d;
}
.login-footer a {
    color: #3498db;
    text-decoration: none;
}
.login-footer a:hover {
    text-decoration: underline;
}
</style>
""", unsafe_allow_html=True)

# Clear any existing admin authentication
if not st.session_state.get("admin_authenticated", False):
    set_admin_auth(False)

# Main app
st.markdown("""
<div class="login-container">
    <div class="login-header">
        <h1>Admin Portal</h1>
        <p>Please enter your credentials to access the admin dashboard</p>
    </div>
""", unsafe_allow_html=True)

# Login form
with st.form("login_form", clear_on_submit=False):
    username = st.text_input("Username", placeholder="Enter your admin username")
    password = st.text_input("Password", type="password", placeholder="Enter your password")
    
    col1, col2 = st.columns(2)
    with col1:
        login_submit = st.form_submit_button("Login", use_container_width=True)
    with col2:
        register_button = st.form_submit_button("Register", use_container_width=True)

# Process login
if login_submit and username and password:
    with st.spinner("Authenticating..."):
        if login("admin_users", username, password):
            set_admin_auth(True, username)
            st.success(f"Welcome, {username}!")
            st.balloons()
            st.switch_page("pages/_admin_dashboard.py")
        else:
            st.error("Invalid credentials! Please check your username and password.")

# Handle register button
if register_button:
    st.switch_page("pages/_admin_registration.py")

# Home button
st.markdown("""
    <div class="login-footer"> Not an administrator? </div>
""", unsafe_allow_html=True)

# Directly add a home button as fallback
if st.button("🏠 Home", use_container_width=True):
    st.switch_page("main.py")

# Add a small footer with system info
st.markdown("""
<div style="position: fixed; bottom: 10px; left: 0; right: 0; text-align: center; font-size: 0.7rem; color: #95a5a6;">
    Medical Monitoring System v1.0 | © 2025 
</div>
""", unsafe_allow_html=True)
