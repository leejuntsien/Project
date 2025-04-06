import psycopg2
from backend_auth import get_db_connection

# Function to count pending comments
def get_pending_comments():
    conn = get_db_connection()
    if not conn:
        return "DB connection error!"
    
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM patient_data pd 
            LEFT JOIN patient_comments pc ON pd.data_id = pc.data_id 
            WHERE pc.comment IS NULL;
        """)
        pending_count = cursor.fetchone()[0]
    
    conn.close()
    return pending_count

# Function to add a new comment
def add_comment(data_id, patient_id, comment):
    conn = get_db_connection()
    if not conn:
        return "DB connection error!"
    
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO patient_comments (data_id, patient_id, comment)
            VALUES (%s, %s, %s)
        """, (data_id, patient_id, comment))
        conn.commit()
    
    conn.close()
    return "Comment added successfully!"

# Function to retrieve all pending comment cases
def get_pending_comment_cases():
    conn = get_db_connection()
    if not conn:
        return "DB connection error!"

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT pd.data_id, pd.patient_id 
            FROM patient_data pd 
            LEFT JOIN patient_comments pc ON pd.data_id = pc.data_id 
            WHERE pc.comment IS NULL;
        """)
        pending_cases = cursor.fetchall()

    conn.close()
    return pending_cases  # Returns a list of (data_id, patient_id)

def total_count():
    conn = get_db_connection()
    if not conn:
        return "DB connection error!"

    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_data")
        total_count = cursor.fetchone()[0]

    conn.close()
    return total_count

