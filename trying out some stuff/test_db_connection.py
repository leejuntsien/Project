import os
import psycopg2
from dotenv import load_dotenv

def get_db_connection():
    """Create a new database connection."""
    import os
    import psycopg2
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
    # Fetch environment variables inside the function
    DB_HOST = os.getenv("DB_HOST", "db")  # Default to 'db' instead of localhost

    DB_NAME = "Patient_data_FYP"  # Ensure this is a valid database in your PostgreSQL instance
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    DB_PORT = os.getenv("DB_PORT", "5432")

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        print(f"[INFO] Connected to database {DB_NAME} at {DB_HOST}:{DB_PORT} as {DB_USER}")
        return conn
    except psycopg2.OperationalError as e:
        print(f"[ERROR] Database connection failed: {e}")
        return None


print(get_db_connection())

username='ppp'
conn = get_db_connection()
if not conn:
    print("Database conn err")

with conn.cursor() as cursor:
    # List all tables in the public schema
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cursor.fetchall()
    print("[INFO] Tables in current database:")
    for table in tables:
        print(" -", table[0])

conn.close()