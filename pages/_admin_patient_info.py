import streamlit as st
from backend_patient_info import get_all_patients, update_patient_password, get_patient_data_count
from utils.security import require_admin_auth, is_admin_authenticated
import pandas as pd

# ✅ FUTURE WORK: Uncomment for encryption
# from cryptography.fernet import Fernet
# SECRET_KEY = b'your-secret-key'  # Store securely in environment variables
# cipher = Fernet(SECRET_KEY)

st.set_page_config(page_title="Patient Information", layout="wide")

# Check authentication
if not is_admin_authenticated():
    st.error("⚠️ Access Denied: Admin authentication required")
    st.warning("Please log in to access the admin dashboard.")
    if st.button("Go to Login"):
        st.switch_page("pages/_admin_auth.py")
    st.stop()

st.title("Patient Information")

# ✅ Get all patients (now includes data_count from JOIN)
patients = get_all_patients()

# ✅ Store password edit states and visibility toggle in session state
if 'password_edits' not in st.session_state:
    st.session_state.password_edits = {}

if 'show_passwords' not in st.session_state:
    st.session_state.show_passwords = False  # Default: Hide passwords

# ✅ Convert patients data to DataFrame for filtering
df = pd.DataFrame(patients, columns=['patient_id', 'username', 'passkey', 'data_count'])

# ✅ Sort by patient_id (default view)
df = df.sort_values(by='patient_id', ascending=True)

# ✅ FUTURE WORK: Uncomment this function to decrypt passwords before displaying
# def decrypt_passkey(encrypted_passkey: bytes) -> str:
#     """Decrypts an encrypted passkey securely."""
#     try:
#         return cipher.decrypt(encrypted_passkey).decode()
#     except Exception:
#         return "Error decrypting"  # Handle cases where decryption fails

# ✅ FUTURE WORK: Apply decryption to passwords before displaying
# df['passkey'] = df['passkey'].apply(lambda x: decrypt_passkey(x) if isinstance(x, bytes) else x)

# Display patients in a table with filters
st.write("### Patient Records")

# ✅ Add filters
col1, col2 = st.columns(2)
with col1:
    search_id = st.text_input("🔍 Filter by Patient ID")
with col2:
    search_username = st.text_input("🔍 Filter by Username")

# ✅ Apply filters
if search_id:
    df = df[df['patient_id'].astype(str).str.contains(search_id, case=False)]
if search_username:
    df = df[df['username'].str.contains(search_username, case=False)]

# ✅ Toggle to **show/hide passwords**
if st.button("🔓 Show Passwords" if not st.session_state.show_passwords else "🔒 Hide Passwords"):
    st.session_state.show_passwords = not st.session_state.show_passwords
    st.rerun()

# ✅ Table Headers
cols = st.columns([3, 3, 3, 3])
cols[0].write("**Patient ID**")
cols[1].write("**Username**")
cols[2].write("**Password (Hashed)**")
cols[3].write("**Actions**")

# Custom CSS for Styling
st.markdown("""
    <style>
        /* Style for patient info container */
        .patient-info-container {
            position: relative;
            cursor: pointer;
            padding: 8px;
            border-radius: 4px;
            transition: background-color 0.2s;
        }
        .patient-info-container:hover {
            background-color: rgba(0, 123, 255, 0.1);
        }
        /* Style for patient info text */
        .data-info {
            color: #007BFF;
            font-weight: bold;
            pointer-events: none;
        }
        /* Invisible button overlay */
        .overlay-button {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            opacity: 0;
            cursor: pointer;
        }
        /* Floating message prompt */
        .floating-prompt {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: blue;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 1000;
            min-width: 300px;
            max-width: 90vw;
        }
        .floating-prompt-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.5);
            z-index: 999;
        }
        /* Password field styling */
        .password-field {
            position: relative;
            display: inline-block;
        }
        .edit-button {
            margin-left: 10px;
            padding: 2px 8px;
            border-radius: 4px;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session states
if "show_prompt" not in st.session_state:
    st.session_state.show_prompt = False
if "selected_patient" not in st.session_state:
    st.session_state.selected_patient = None
if "prompt_message" not in st.session_state:
    st.session_state.prompt_message = ""

@st.dialog("Confirm switch page")
def switch_page_dialog(patient_id):
    st.write(f"Comfirm switch page to {patient_id}'s data?")
    st.query_params["id"] = patient_id
    st.session_state.patient_id = patient_id
        
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ View Details"):
            # Process the "View Details" action
            st.session_state.show_prompt = False  # Hide the prompt
            
            # ✅ Ensure selected_patient exists before using it
            if "selected_patient" in st.session_state:               
                # ✅ Navigate to another page
                st.switch_page("pages/Admin_multi_data.py")
            else:
                st.warning("No patient selected! Please select a patient first.")
                
    with col2:
        if st.button("❌ Close"):
                # Close the dialog without action
                st.session_state.show_prompt = False  # Close the modal
                st.session_state.selected_patient = None  # Reset any selections
                st.query_params["id"] = None
                st.rerun()  # Refresh the page   


# Display Patients' Information with Overlayed Buttons
for _, row in df.iterrows():
    patient_id, username, passkey, data_count = row

    # Streamlit Columns for Layout
    cols = st.columns([2, 3, 3, 3])

    with cols[0]:
        st.markdown("""
                <style>
                    /* Tooltip container */
                    .tooltip-container {
                        position: relative;
                        display: inline-block;
                    }

                    /* Tooltip text */
                    .tooltip-container .tooltiptext {
                        visibility: hidden;
                        width: 200px;
                        background-color: #333;
                        color: white;
                        text-align: center;
                        padding: 5px;
                        border-radius: 6px;
                        
                        /* Position the tooltip text */
                        position: absolute;
                        z-index: 1;
                        bottom: 125%;
                        left: 50%;
                        margin-left: -100px;
                        
                        /* Fade in tooltip */
                        opacity: 0;
                        transition: opacity 0.3s;
                    }

                    /* Tooltip arrow */
                    .tooltip-container .tooltiptext::after {
                        content: "";
                        position: absolute;
                        top: 100%;
                        left: 50%;
                        margin-left: -5px;
                        border-width: 5px;
                        border-style: solid;
                        border-color: #333 transparent transparent transparent;
                    }

                    /* Show the tooltip text when you hover over the tooltip container */
                    .tooltip-container:hover .tooltiptext {
                        visibility: visible;
                        opacity: 1;
                    }
                </style>
            """, unsafe_allow_html=True)
        
        col1,col2=st.columns([1,1])
        with col1:
            # HTML Element for Hover Info
            st.markdown(
                    f"""
                    <div class="tooltip-container">
                        <span class="data-info">{patient_id}</span>
                        <span class="tooltiptext">Number of datasets: {data_count}</span>
                    </div>
                    """, unsafe_allow_html=True)
        with col2:
            # Invisible overlay button
            if st.button("View", key=f"view_{patient_id}", help=f"View details for Patient {patient_id}", type="tertiary"):
                st.session_state.show_prompt = True
                st.session_state.selected_patient = patient_id
                st.rerun()

    with cols[1]:
        cols1,cols2=st.columns([1,3])    
        with cols1:
            pass
        with cols2:
            st.markdown(f"""
                <div class="patient-info-container">
                    <div class="data-info">{username}</div>
                </div>
            """, unsafe_allow_html=True)

        # Password field
        with cols[2]:
            if patient_id not in st.session_state.password_edits:
                st.session_state.password_edits[patient_id] = False
            
            if st.session_state.password_edits[patient_id]:
                # ✅ Show password edit field
                new_password = cols[2].text_input("New Password", 
                                            key=f"pass_{patient_id}",
                                            type="password")
            if cols[3].button("Save", key=f"save_{patient_id}"):
                    if new_password:
                        # ✅ FUTURE WORK: Encrypt before storing
                        # encrypted_password = cipher.encrypt(new_password.encode())
                        update_patient_password(patient_id, new_password)  # Change to encrypted_password when ready
                        st.session_state.password_edits[patient_id] = False
                        st.success(f"Password updated for patient {patient_id}")
                        st.rerun()
                    else:
                        st.error("Password cannot be empty")
            else:
            # ✅ Show password field based on toggle
                display_passkey = passkey if st.session_state.show_passwords else "********"
            cols[2].write(display_passkey)
        
            # ✅ Change password button
            if cols[3].button("Change Password", key=f"edit_{patient_id}"):
                    st.session_state.password_edits[patient_id] = True
                    st.rerun()
# Floating message prompt
# Create a container for the prompt (acting as a popup)
if st.session_state.show_prompt:
    switch_page_dialog(patient_id=st.session_state.selected_patient)

# ✅ Refresh Data Button (In-Page)
if st.button("🔄 Refresh Data", key="refresh_main"):
    st.session_state.password_edits = {}  # Reset any ongoing password edits
    st.rerun()

# ✅ Back to Admin Dashboard Button (In-Page)
if st.button("👩🏻‍💻 Back To Admin Dashboard", key="back_main"):
    st.switch_page("pages/_admin_dashboard.py")
    st.stop()

# 🛠 Sidebar Navigation
st.sidebar.title("Navigation")

# ✅ Refresh Data Button in Sidebar (Unique Key)
if st.sidebar.button("🔄 Refresh Data", key="refresh_sidebar"):
    st.session_state.password_edits = {}  # Reset any ongoing password edits
    st.rerun()

# ✅ Back to Admin Dashboard Button in Sidebar (Unique Key)
if st.sidebar.button("👩🏻‍💻 Back To Admin Dashboard", key="back_sidebar"):
    st.switch_page("pages/_admin_dashboard.py")
    st.stop()