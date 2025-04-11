
import streamlit as st
from backend_auth import login, register_admin
from utils.security import require_admin_auth, is_admin_authenticated, set_admin_auth
from utils.admin_ui import load_admin_css, format_button, show_toast, optimize_streamlit

st.set_page_config(page_title="Admin Registration", layout="centered")

# Load custom CSS
load_admin_css()

# Apply optimizations
optimize_streamlit()

# Add a custom background for the registration page
st.markdown("""
<style>
.main .block-container {
    background-image: 
        linear-gradient(rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0.95)),
        url("data:image/svg+xml,%3Csvg width='80' height='80' viewBox='0 0 80 80' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%233b82f6' fill-opacity='0.05'%3E%3Cpath d='M0 0h40v40H0V0zm40 40h40v40H40V40zm0-40h2l-2 2V0zm0 4l4-4h2l-6 6V4zm0 4l8-8h2L40 10V8zm0 4L52 0h2L40 14v-2zm0 4L56 0h2L40 18v-2zm0 4L60 0h2L40 22v-2zm0 4L64 0h2L40 26v-2zm0 4L68 0h2L40 30v-2zm0 4L72 0h2L40 34v-2zm0 4L76 0h2L40 38v-2zm0 4L80 0v2L42 40h-2zm4 0L80 4v2L46 40h-2zm4 0L80 8v2L50 40h-2zm4 0l28-28v2L54 40h-2zm4 0l24-24v2L58 40h-2zm4 0l20-20v2L62 40h-2zm4 0l16-16v2L66 40h-2zm4 0l12-12v2L70 40h-2zm4 0l8-8v2l-6 6h-2zm4 0l4-4v2l-2 2h-2z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}

/* Add animation for the form */
.registration-form {
    animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.auth-card {
    background-color: white;
    border-radius: 10px;
    padding: 2rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
    border-top: 4px solid #3b82f6;
    max-width: 600px;
    margin: 0 auto;
}

/* Improve input fields */
div[data-baseweb="input"] {
    margin-bottom: 1rem;
}

/* Add icon to input fields */
.input-with-icon {
    position: relative;
}

.input-with-icon i {
    position: absolute;
    left: 10px;
    top: 50%;
    transform: translateY(-50%);
    color: #6b7280;
}

.input-with-icon input {
    padding-left: 30px !important;
}
</style>
""", unsafe_allow_html=True)

if not is_admin_authenticated():
    st.markdown("""
    <div class="auth-card registration-form">
        <h1 style="color: #1e40af; text-align: center;">⚠️ Admin Authentication Required</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.warning("You must be logged in as an admin to access this page.")
    
    with st.container():
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.subheader("Admin Login")
        
        auth_username = st.text_input("Admin Username", placeholder="Enter your admin username")
        auth_password = st.text_input("Admin Password", type="password", placeholder="Enter your password")

        col1, col2 = st.columns(2)
        
        with col1:
            if format_button("Login", key="login_btn", type="primary"):
                if login("admin_users", auth_username, auth_password):
                    set_admin_auth(True, auth_username)
                    show_toast("Authentication successful!", "success")
                    st.rerun()
                else:
                    show_toast("Authentication failed. Only registered admins can access this page.", "error")
        
        with col2:
            if st.button("Back to Login", key="back_btn", type="secondary"):
                    st.switch_page("pages/_admin_auth.py")
        
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="auth-card registration-form">
        <h1 style="color: #1e40af; text-align: center;">Register a New Admin</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.info(f"Logged in as: {st.session_state.get('admin_username')}")

    with st.container():
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        
        st.subheader("Create New Admin Account")
        
        new_username = st.text_input("New Admin Username", placeholder="Enter username for new admin")
        new_password = st.text_input("New Admin Password", type="password", placeholder="Enter strong password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm password")

        # Password strength indicator
        if new_password:
            strength = 0
            feedback = []
            
            if len(new_password) >= 8:
                strength += 1
            else:
                feedback.append("Password should be at least 8 characters")
                
            if any(c.isdigit() for c in new_password):
                strength += 1
            else:
                feedback.append("Include at least one number")
                
            if any(c.isupper() for c in new_password):
                strength += 1
            else:
                feedback.append("Include at least one uppercase letter")
                
            if any(not c.isalnum() for c in new_password):
                strength += 1
            else:
                feedback.append("Include at least one special character")
            
            # Display strength bar
            strength_color = ["#ef4444", "#f59e0b", "#84cc16", "#10b981"][min(strength, 3)]
            strength_width = f"{25 * (strength + 1)}%"
            strength_text = ["Weak", "Fair", "Good", "Strong"][min(strength, 3)]
            
            st.markdown(f"""
            <div style="margin-bottom: 20px;">
                <p>Password Strength: <strong>{strength_text}</strong></p>
                <div style="background-color: #e2e8f0; height: 8px; border-radius: 4px;">
                    <div style="background-color: {strength_color}; width: {strength_width}; height: 8px; border-radius: 4px;"></div>
                </div>
                <ul style="color: #64748b; font-size: 0.875rem; margin-top: 8px;">
                    {"".join([f"<li>• {item}</li>" for item in feedback])}
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            # Check if passwords match
            if new_password and confirm_password:
                if new_password != confirm_password:
                    st.warning("Passwords do not match")

        col1, col2, col3 = st.columns(3)
        with col1:
            register_disabled = not (new_username and new_password and new_password == confirm_password)
            if format_button("Register New Admin", key="register_btn", type="success", disabled=register_disabled):
                if new_username and new_password:
                    if new_password == confirm_password:
                        message = register_admin(st.session_state["admin_username"], new_username, new_password)
                        show_toast(message, "success")
                        st.switch_page("pages/_admin_auth.py")
                    else:
                        show_toast("Passwords do not match", "error")
                else:
                    show_toast("Please fill in all fields", "warning")
        
        with col2:
                if st.button("🚪 Logout"):
                    if st.session_state.get("logout_confirmed", False):
                        st.session_state.clear()  # Clears session data
                        st.success("Logged out successfully!")
                        st.switch_page("pages/_admin_auth.py")  # Redirect to login page
                    else:
                        st.session_state["logout_confirmed"] = True
                        st.warning("Click Logout again to confirm.")
        
        with col3:
            # Home Button
            if st.button("🏠 Home", key="home_btn", type="secondary"):
                    st.switch_page("main.py")
        
        st.markdown('</div>', unsafe_allow_html=True)
