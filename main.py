
import streamlit as st
from backend_auth import get_db_connection
from dotenv import load_dotenv
import os
import base64

# Load .env from common locations
env_files = [
    os.path.join('.env', 'FYP_webapp.env'),
    '.env',
    '../.env',
]

for env_file in env_files:
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"[INFO] Loaded environment variables from {env_file}")
        break
else:
    print("[WARN] No .env found. Falling back to system env.")
    
st.set_page_config(
    page_title="Medical Monitoring System", 
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="🏥"
)

# Function to add background image
def add_bg_from_local(image_file):
    with open(image_file, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{encoded_string}");
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        
        /* Add overlay to make content readable */
        .stApp::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(255, 255, 255, 0.85);  /* White overlay with 85% opacity */
            z-index: -1;
        }}
        
        /* Make text pop with drop shadows */
        h1, h2, h3, .main-title, .subtitle {{
            text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }}
        
        /* Enhance cards with subtle shadows and hover effects */
        .card {{
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            background-color: rgba(255, 255, 255, 0.9);
        }}
        
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 12px 24px rgba(0,0,0,0.2);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Add custom pattern background option
def add_pattern_background(pattern_type="circles"):
    patterns = {
        "circles": """
            background-color: #f9f9f9;
            background-image: radial-gradient(#2E7DAF 0.5px, transparent 0.5px), radial-gradient(#2E7DAF 0.5px, #f9f9f9 0.5px);
            background-size: 20px 20px;
            background-position: 0 0, 10px 10px;
        """,
        "grid": """
            background-color: #f9f9f9;
            background-image: linear-gradient(#2E7DAF 1px, transparent 1px), linear-gradient(to right, #2E7DAF 1px, #f9f9f9 1px);
            background-size: 20px 20px;
        """,
        "diagonal": """
            background: linear-gradient(45deg, #f9f9f9 25%, transparent 25%, transparent 75%, #f9f9f9 75%, #f9f9f9),
                        linear-gradient(45deg, #f9f9f9 25%, transparent 25%, transparent 75%, #f9f9f9 75%, #f9f9f9);
            background-color: #ffffff;
            background-size: 20px 20px;
            background-position: 0 0, 10px 10px;
        """
    }
    
    st.markdown(
        f"""
        <style>
        .stApp {{
            {patterns.get(pattern_type, patterns["circles"])}
        }}
        
        /* Add overlay to make content readable */
        .stApp::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(255, 255, 255, 0.7);  /* White overlay with 70% opacity */
            z-index: -1;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Choose between background image or pattern
# Uncomment ONE of these lines to use:
try:
    # Option 1: Use a doggie background image
    add_bg_from_local("frontend/static/puppy_attack_doctor.png")
    
    # Option 2: Use a pattern background instead (comment the above line and uncomment below)
    # add_pattern_background("circles")  # options: "circles", "grid", "diagonal"
except Exception as e:
    st.warning(f"Could not set custom background: {str(e)}")
    # Fallback to a pattern background if image fails
    add_pattern_background("circles")

# Apply custom CSS styling
st.markdown("""
<style>
    .main-title {
        font-size: 36px !important;
        font-weight: 700 !important;
        color: #2E4057 !important;
        margin-bottom: 8px !important;
        text-align: center;
    }
    .subtitle {
        font-size: 20px !important;
        color: #48556B !important;
        margin-bottom: 30px !important;
        text-align: center;
    }
    .card {
        border-radius: 10px;
        padding: 20px;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
    }
    .card-title {
        font-size: 20px !important;
        font-weight: 600 !important;
        margin-bottom: 15px !important;
        color: #2E4057 !important;
    }
    .accent-text {
        color: #0366d6 !important;
        font-weight: 600 !important;
    }
    .btn-custom {
        background-color: #0366d6;
        color: white;
        padding: 12px 24px;
        border-radius: 5px;
        font-weight: 600;
        border: none;
        cursor: pointer;
        transition: background-color 0.3s ease;
        text-align: center;
        display: inline-block;
        text-decoration: none;
        margin: 4px 2px;
    }
    .btn-custom:hover {
        background-color: #0258b8;
    }
    .centered-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 100%;
        margin-top: 30px;
    }
    .stButton>button {
        width: 100%;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: 600;
        border-radius: 5px;
    }
    footer {
        margin-top: 50px;
        text-align: center;
        color: #6c757d;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Main header
#st.markdown('<p class="main-title">Patient Monitoring System</p>', unsafe_allow_html=True)
st.markdown("""
<div style="background-color: rgba(255, 255, 255, 0.8); padding: 20px; border-radius: 10px;">
    <h1 style="text-align: center; color: #2E4057;">Patient Monitoring System</h1>
    <p style="text-align: center; color: #48556B;">
        Real-time medical data monitoring and analysis.
    </p>
</div>
""", unsafe_allow_html=True)
# Read image and encode
try:
    with open("frontend/static/puppy_attack_doctor.png", "rb") as f:
        data = f.read()
        encoded = base64.b64encode(data).decode()

    # Animated image display
    st.markdown(
        f"""
        <div style="text-align:center; margin-bottom: 30px;">
            <img src="data:image/png;base64,{encoded}" alt="Puppy Attack!" width="300" 
                 style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); animation: wiggle 2s ease-in-out infinite;">
        </div>

        <style>
        @keyframes wiggle {{
          0% {{ transform: rotate(0deg); }}
          25% {{ transform: rotate(1deg); }}
          50% {{ transform: rotate(-1deg); }}
          75% {{ transform: rotate(1deg); }}
          100% {{ transform: rotate(0deg); }}
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
except Exception as e:
    st.warning(f"Image not found: {str(e)}")

# Introduction card
st.markdown("""
<div class="card">
    <p class="card-title">Welcome to our Medical Monitoring System</p>
    <p>This platform provides real-time monitoring of patient vital signs and health metrics, 
    allowing healthcare professionals to track patient health remotely and respond quickly to changes.</p>
    <p>Our system supports:</p>
    <ul>
        <li>Real-time vital sign monitoring</li>
        <li>Historical data analysis</li>
        <li>Medical device integration</li>
        <li>Secure patient data management</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Login columns
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown('<div class="centered-content">', unsafe_allow_html=True)
    
    st.markdown('<div style="background-color: rgba(255, 255, 255, 0.8); padding: 10px; border-radius: 10px;"><p class="card-title" style="text-align: center;">Access the Platform</p></div>', unsafe_allow_html=True)
    
    cols1, cols2, cols3 =st.columns([1,1,1])
    with cols1:
        if st.button("Patient Login", key="patient_login_btn", help="Login as a patient to view your health data"):
            st.switch_page("pages/patient_auth.py")
    with cols3:
        if st.button("Administrator Access", key="admin_login_btn", help="Login as an administrator to manage patients and view all data"):
            st.switch_page("pages/_admin_auth.py")
    
    # Check database connection
    conn_status_container = st.container()
    with conn_status_container:
        st.markdown('    <div style="background-color: rgba(255, 255, 255, 0.8); padding: 5px; border-radius: 5px;">'
        '<p style="text-align: center; margin-top: 20px;">Database Status:</p></div>', unsafe_allow_html=True)
        
        conn = get_db_connection()
        if conn:
            st.success("✅ Database connection active")
            conn.close()
        else:
            st.error("❌ Database connection failed")

    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""

    <footer>
        <div style="background-color: rgba(255, 255, 255, 0.8); padding: 10px; border-radius: 10px;">
        <p>© 2025 Patient Monitoring System | Final Year Project</p>
        <p>For assistance, please contact the system administrator.</p>
        </div>
     </footer>

""", unsafe_allow_html=True)
