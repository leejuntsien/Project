import psycopg2
from backend_auth import get_db_connection, hash_password

# ✅ FUTURE WORK: Uncomment when using encryption
# from cryptography.fernet import Fernet
# SECRET_KEY = b'your-secret-key'  # Store securely in environment variables
# cipher = Fernet(SECRET_KEY)

def get_all_patients():
    """Retrieve all patients along with their data count."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            p.patient_id, 
            p.username, 
            p.passkey,  -- Ensures passwords are included
            COALESCE(COUNT(pd.patient_id), 0) AS data_count
        FROM patients p
        LEFT JOIN patient_data pd ON p.patient_id = pd.patient_id 
        GROUP BY p.patient_id, p.username, p.passkey
    """)

    patients = cursor.fetchall()
    cursor.close()
    conn.close()
    # ✅ FUTURE WORK: Uncomment to decrypt passwords before returning data
    # patients = [(pid, user, decrypt_passkey(passkey), data_count) for pid, user, passkey, data_count in patients]

    return patients

# ✅ FUTURE WORK: Add this decryption function when encryption is enabled
# def decrypt_passkey(encrypted_passkey: bytes) -> str:
#     """Decrypts an encrypted passkey securely."""
#     try:
#         return cipher.decrypt(encrypted_passkey).decode()
#     except Exception:
#         return "Error decrypting"



def update_patient_password(patient_id: str, new_password: str):
    """Update a patient's password"""
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(new_password)
    cursor.execute("UPDATE patients SET passkey = %s WHERE patient_id = %s", 
                  (hashed_password, patient_id))
    conn.commit()
    cursor.close()
    conn.close()

def get_patient_data_count(patient_id: str):
    """Get count of data entries for a specific patient"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM patient_data 
        WHERE patient_id = %s
    """, (patient_id,))
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count

def get_patient_data(patient_id: str = None, filters: dict = None):
    """Get patient data with optional filters"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
    SELECT 
        pd.patient_id,
        pd.data_id,
        pd.created_at,
        COUNT(pd.patient_id) AS num_instances
    FROM patient_data pd
    """
    
    params = []
    conditions = []

    if patient_id:
        conditions.append("pd.patient_id = %s")
        params.append(patient_id)

    if filters:
        for key, value in filters.items():
            if value:
                conditions.append(f"pd.{key} = %s")
                params.append(value)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # ✅ Add GROUP BY to avoid the error
    query += " GROUP BY pd.patient_id, pd.data_id, pd.created_at"

    # ✅ Ensure ordering after grouping
    query += " ORDER BY pd.created_at DESC"

    cursor.execute(query, tuple(params))
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data


def get_data_instance(data_id: str):
    """Get a single data instance with all details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pd.*, p.username 
        FROM patient_data pd
        JOIN patients p ON pd.patient_id = p.patient_id
        WHERE pd.data_id = %s
    """, (data_id,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()
    return data

def get_patient_summary():
    
     conn = get_db_connection()
     cursor = conn.cursor()
    
     query = """
    SELECT
        p.patient_id,
        p.username,
        COUNT(pd.patient_id) AS num_instances,
        MAX(pd.created_at) AS latest
    FROM 
        patients p
    JOIN 
        patient_data pd
        ON p.patient_id = pd.patient_id
    GROUP BY 
        p.patient_id
    """
    
     cursor.execute(query)
     result = cursor.fetchall()  # Fetch all the results from the query
    
     patient_summary = {}
    
    # Store the result in a dictionary with patient_id as the key
     for row in result:
        patient_id, username, num_instances, latest = row
        patient_summary[patient_id] = {
            'username': username,
            'num_instances': num_instances,
            'latest': latest
        }
    
     conn.close()  # Don't forget to close the connection
    
     return patient_summary

def print_patient_data_columns():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query to get column names from the patient_data table
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'patient_data';
    """)
    
    # Fetch and print column names
    columns = cursor.fetchall()
    print("Columns in patient_data table:")
    for column in columns:
        print(column[0])
    
    cursor.close()
    conn.close()

# Call the function to print column names
print_patient_data_columns()
#print(get_patient_summary())