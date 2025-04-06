import streamlit as st
from backend_auth import login, register_user, update_user_password, user_exists, get_patient_id, get_db_connection

st.set_page_config(page_title="Patient Authentication")

st.title("Patient Login")

# Initialize session state for login fields
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "password" not in st.session_state:
    st.session_state["password"] = ""

# Persistent Inputs
st.session_state["username"] = st.text_input("Username", value=st.session_state["username"])
st.session_state["password"] = st.text_input("Password", type="password", value=st.session_state["password"])

# **Login Function**
if st.button("Login"):
    login_result = login("patients", st.session_state["username"], st.session_state["password"])

    if login_result:
        patient_id = get_patient_id(st.session_state["username"])  # Get the patient ID from the database
        if patient_id:
            st.session_state["patient_id"] = patient_id  # Store in session
            st.success(f"Welcome, {st.session_state['username']}!")
            st.switch_page("pages/patient_dashboard.py")  # Redirect to dashboard
        else:
            st.error("User not found in the database!")
    else:
        st.error("Invalid username or password!")

# Forgot Password / Register Handling
if "forgot_password" not in st.session_state:
    st.session_state["forgot_password"] = False

if st.button("Register / Forgot Password"):
    if not st.session_state["username"]:
        st.warning("Please enter a username to proceed.")  
    else:
        st.session_state["forgot_password"] = True  # Keep popover open

# **POPUP for Reset Password**
if st.session_state["forgot_password"]:
    with st.popover("🔑 Reset Password"):  # This is now a pop-up
        if user_exists(st.session_state["username"]):
            st.warning("User exists! If you forgot your password, contact admin.")

            # Admin Authentication Section
            if "admin_authenticated" not in st.session_state:
                st.session_state["admin_authenticated"] = False

            admin_user = st.text_input("Admin Username", key="admin_user")
            admin_pass = st.text_input("Admin Password", type="password", key="admin_pass")

            if st.button("Admin Authenticate"):
                if login("admin_users", admin_user, admin_pass):
                    st.session_state["admin_authenticated"] = True
                    st.success("Admin authenticated successfully!")
                else:
                    st.error("Invalid admin credentials!")

            if st.session_state["admin_authenticated"]:
                new_password = st.text_input("Enter New Password", type="password", key="new_pass")
                if st.button("Update Password"):
                    result = update_user_password(st.session_state["username"], new_password)
                    st.success(result)

                    # **Automatically close the pop-up after success**
                    st.session_state["forgot_password"] = False  
                    st.session_state["admin_authenticated"] = False
        else:
            st.warning("User does not exist! Please register.")

# **Registration Form**
with st.expander("New User Registration"):
    new_username = st.text_input("New Username")
    new_password = st.text_input("New Password", type="password")

    if st.button("Register"):
        if user_exists(new_username):
            st.warning("Username already exists! Please log in.")
        else:
            register_result = register_user(new_username, new_password)
            st.success(register_result)

# **Home Button**
if st.button("🏠 Home"):
    st.switch_page("main.py")  # Redirect to main.py




