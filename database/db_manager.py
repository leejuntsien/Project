import os
import sys
import psycopg2
from psycopg2 import pool  # Correct import for the pool module
import asyncpg
import asyncio
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import threading
import atexit
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_manager')

# Load environment variables from the correct path
def load_env_vars():
    env_path = os.path.join('.env', 'FYP_webapp.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"Loaded environment variables from {env_path}")
        return True
    else:
        logger.warning(f"Environment file not found at {env_path}")
        # Try alternative locations as fallback
        if os.path.exists('.env'):
            load_dotenv('.env')
            logger.info("Loaded environment variables from .env")
            return True
        elif os.path.exists('../.env'):
            load_dotenv('../.env')
            logger.info("Loaded environment variables from ../.env")
            return True
        else:
            logger.warning("No .env file found. Using default or system environment variables.")
            return False

# Load environment variables
load_env_vars()

# Database connection parameters
DB_HOST = os.getenv("DB_HOST", "db")  # Default to 'db' instead of localhost
DB_NAME = os.getenv("DB_NAME", "Patient_data_FYP")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = os.getenv("DB_PORT", "5432")

# Temp table management settings
TEMP_TABLE_CLEANUP_INTERVAL = int(os.getenv("TEMP_TABLE_CLEANUP_INTERVAL", "300"))  # 5 minutes by default
TEMP_DATA_MAX_AGE = int(os.getenv("TEMP_DATA_MAX_AGE", "3600"))  # 1 hours by default

# Connection pool settings
MIN_CONNECTIONS = int(os.getenv("DB_MIN_CONNECTIONS", "1"))
MAX_CONNECTIONS = int(os.getenv("DB_MAX_CONNECTIONS", "10"))

# Fallback schema if schema.sql file is not found
FALLBACK_SCHEMA = """
-- Create patient_trials table if it doesn't exist
CREATE TABLE IF NOT EXISTS patient_trials (
    trial_id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    notes TEXT
);

-- Create live_patient_data table if it doesn't exist
CREATE TABLE IF NOT EXISTS live_patient_data (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    sensor_data JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create trial_temp table if it doesn't exist
CREATE TABLE IF NOT EXISTS trial_temp (
    id SERIAL PRIMARY KEY,
    trial_id INTEGER REFERENCES patient_trials(trial_id),
    patient_id INTEGER NOT NULL,
    sensor_data JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create sensor_data table if it doesn't exist (for server.py compatibility)
CREATE TABLE IF NOT EXISTS sensor_data (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    device_id TEXT,
    sensor_data JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Singleton pattern for database manager
class DatabaseManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.sync_pool = None
        self.async_pool = None
        self.schema_initialized = False
        self.cleanup_thread = None
        self.is_running = False
        self.schema_init_attempts = 0
        self.max_schema_init_attempts = 3
        
        # Register cleanup on exit
        atexit.register(self.shutdown)
    
    def get_schema_path(self):
        """Get the path to the schema.sql file"""
        # Try different possible locations
        possible_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'init.sql'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'init.sql'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'init.sql'),
            './database/init.sql',
            '../database/init.sql',
            './init.sql',
            '../init.sql'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found schema file at: {path}")
                return path
        
        logger.error("Schema file not found in any of the expected locations. Using fallback schema.")
        return None
    
    def init_sync_pool(self):
        """Initialize the synchronous connection pool for psycopg2"""
        if self.sync_pool is not None:
            return self.sync_pool
            
        try:
            # First try with quoted database name (for names with spaces)
            try:
                logger.info(f"Attempting to connect to database with quoted name: \"{DB_NAME}\"")
                self.sync_pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=MIN_CONNECTIONS,
                    maxconn=MAX_CONNECTIONS,
                    host=DB_HOST,
                    database=f'"{DB_NAME}"',  # Quote the database name
                    user=DB_USER,
                    password=DB_PASSWORD,
                    port=DB_PORT
                )
                logger.info("Synchronous database pool created with quoted name")
            except psycopg2.Error as e:
                logger.warning(f"First connection attempt failed: {e}")
                # Try without quotes
                logger.info(f"Attempting to connect to database without quotes: {DB_NAME}")
                self.sync_pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=MIN_CONNECTIONS,
                    maxconn=MAX_CONNECTIONS,
                    host=DB_HOST,
                    database=DB_NAME,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    port=DB_PORT
                )
                logger.info("Synchronous database pool created without quotes")
            
            # Test the connection
            conn = self.sync_pool.getconn()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            self.sync_pool.putconn(conn)
            
            return self.sync_pool
            
        except psycopg2.Error as e:
            logger.error(f"Failed to create synchronous database pool: {e}")
            return None
    
    async def init_async_pool(self):
        """Initialize the asynchronous connection pool for asyncpg"""
        if self.async_pool is not None:
            return self.async_pool
            
        try:
            # Try with direct parameters
            logger.info(f"Attempting to connect to database: {DB_NAME}")
            self.async_pool = await asyncpg.create_pool(
                host=DB_HOST,
                port=int(DB_PORT),
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                min_size=MIN_CONNECTIONS,
                max_size=MAX_CONNECTIONS,
                command_timeout=60.0,
                server_settings={
                    'client_encoding': 'utf8',
                    'application_name': 'db_manager'
                }
            )
            logger.info("Asynchronous database pool created successfully")
            
            # Test the connection
            async with self.async_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            return self.async_pool
            
        except Exception as e:
            logger.error(f"Failed to create asynchronous database pool: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            return None
    
    def init_db(self):
        """Initialize the database with schema from schema.sql"""
        if self.schema_initialized:
            return True
            
        # Increment attempt counter
        self.schema_init_attempts += 1
        
        if self.schema_init_attempts > self.max_schema_init_attempts:
            logger.error(f"Failed to initialize schema after {self.max_schema_init_attempts} attempts. Giving up.")
            return False
            
        logger.info(f"Initializing database schema (attempt {self.schema_init_attempts})...")
        
        # Get the path to the schema.sql file
        schema_path = self.get_schema_path()
        
        # Read the schema SQL
        if schema_path:
            try:
                with open(schema_path, 'r') as f:
                    schema_sql = f.read()
                    logger.info(f"Loaded schema SQL from {schema_path} ({len(schema_sql)} bytes)")
            except Exception as e:
                logger.error(f"Error reading schema file: {e}")
                schema_sql = FALLBACK_SCHEMA
                logger.info("Using fallback schema")
        else:
            schema_sql = FALLBACK_SCHEMA
            logger.info("Using fallback schema")
        
        # Get a connection from the pool
        pool = self.init_sync_pool()
        if not pool:
            logger.error("Cannot initialize schema: database pool not available")
            return False
        
        conn = pool.getconn()
        try:
            # Create a cursor
            cur = conn.cursor()
            
            # Execute the schema SQL
            logger.info("Executing schema SQL...")
            cur.execute(schema_sql)
            
            # Commit the changes
            conn.commit()
            
            # Close the cursor
            cur.close()
            
            # Verify tables were created
            cur = conn.cursor()
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [row[0] for row in cur.fetchall()]
            cur.close()
            
            logger.info(f"Tables in database: {', '.join(tables)}")
            
            required_tables = ['patient_trials', 'live_patient_data', 'trial_temp', 'sensor_data']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                logger.error(f"Schema initialization incomplete. Missing tables: {', '.join(missing_tables)}")
                return False
            
            self.schema_initialized = True
            logger.info("Database schema initialized successfully")
            return True
            
        except psycopg2.Error as e:
            logger.error(f"Schema initialization error: {e}")
            logger.error(traceback.format_exc())
            conn.rollback()
            return False
        finally:
            # Return the connection to the pool
            pool.putconn(conn)
    
    async def ensure_tables_exist(self):
        """Check if required tables exist and initialize if they don't"""
        if self.schema_initialized:
            return True
            
        pool = await self.init_async_pool()
        if not pool:
            logger.error("Cannot check tables: database pool not available")
            return False
        
        try:
            async with pool.acquire() as conn:
                # Check if required tables exist
                tables_exist = True
                required_tables = ['patient_trials', 'live_patient_data', 'trial_temp', 'sensor_data']
                
                for table in required_tables:
                    exists = await conn.fetchval(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = '{table}'
                        )
                    """)
                    
                    if not exists:
                        tables_exist = False
                        logger.warning(f"Table '{table}' does not exist")
                
                if not tables_exist:
                    logger.info("Required tables don't exist. Initializing database schema...")
                    # We need to initialize the schema
                    # Since we're in an async context, we'll run the sync init_db in a thread
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, self.init_db)
                    
                    if not result:
                        # If sync initialization failed, try to create tables directly with asyncpg
                        logger.info("Trying to create tables directly with asyncpg...")
                        try:
                            async with pool.acquire() as conn:
                                await conn.execute(FALLBACK_SCHEMA)
                            logger.info("Tables created successfully with asyncpg")
                            self.schema_initialized = True
                            return True
                        except Exception as e:
                            logger.error(f"Failed to create tables with asyncpg: {e}")
                            return False
                    
                    return result
                else:
                    self.schema_initialized = True
                    logger.info("Required tables already exist")
                    return True
                    
        except Exception as e:
            logger.error(f"Error checking tables: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def cleanup_temp_tables(self):
        """Clean up old data from temporary tables"""
        pool = self.init_sync_pool()
        if not pool:
            logger.error("Cannot clean up temp tables: database pool not available")
            return
        
        conn = pool.getconn()
        try:
            # Create a cursor
            cur = conn.cursor()
            
            # Get current time minus max age
            cutoff_time = datetime.now() - timedelta(seconds=TEMP_DATA_MAX_AGE)
            
            # Delete old data from trial_temp
            try:
                cur.execute("""
                    DELETE FROM trial_temp
                    WHERE timestamp < %s
                """, (cutoff_time,))
                deleted_count = cur.rowcount
                logger.info(f"Deleted {deleted_count} old records from trial_temp")
            except psycopg2.Error as e:
                logger.error(f"Error cleaning up trial_temp: {e}")
            
            # Delete old data from live_patient_data
            try:
                cur.execute("""
                    DELETE FROM live_patient_data
                    WHERE timestamp < %s
                """, (cutoff_time,))
                deleted_count = cur.rowcount
                logger.info(f"Deleted {deleted_count} old records from live_patient_data")
            except psycopg2.Error as e:
                logger.error(f"Error cleaning up live_patient_data: {e}")
            
            # Commit the changes
            conn.commit()
            
        except psycopg2.Error as e:
            logger.error(f"Error cleaning up temp tables: {e}")
            conn.rollback()
        finally:
            # Return the connection to the pool
            pool.putconn(conn)
    
    def start_cleanup_thread(self):
        """Start a background thread to periodically clean up temp tables"""
        if self.cleanup_thread is not None and self.cleanup_thread.is_alive():
            return  # Thread already running
        
        self.is_running = True
        
        def cleanup_worker():
            while self.is_running:
                try:
                    # Make sure schema is initialized
                    if not self.schema_initialized:
                        self.init_db()
                    
                    # Clean up temp tables
                    self.cleanup_temp_tables()
                    
                except Exception as e:
                    logger.error(f"Error in cleanup thread: {e}")
                
                # Sleep until next cleanup
                for _ in range(TEMP_TABLE_CLEANUP_INTERVAL):
                    if not self.is_running:
                        break
                    time.sleep(1)
        
        self.cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        logger.info(f"Started temp table cleanup thread (interval: {TEMP_TABLE_CLEANUP_INTERVAL}s)")
    
    def shutdown(self):
        """Shut down the database manager and clean up resources"""
        logger.info("Shutting down database manager...")
        
        # Stop the cleanup thread
        self.is_running = False
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        
        # Close the sync pool
        if self.sync_pool:
            self.sync_pool.closeall()
            logger.info("Closed synchronous connection pool")
        
        # Close the async pool (needs to be done in an async context)
        # This will be handled by the application shutdown

# Create a singleton instance
db_manager = DatabaseManager()

# Convenience functions for external use
def get_sync_connection():
    """Get a synchronous database connection"""
    pool = db_manager.init_sync_pool()
    if not pool:
        raise Exception("Database pool not available")
    
    # Ensure schema is initialized
    if not db_manager.schema_initialized:
        db_manager.init_db()
    
    return pool.getconn()

def release_sync_connection(conn):
    """Release a synchronous database connection back to the pool"""
    if db_manager.sync_pool and conn:
        db_manager.sync_pool.putconn(conn)

async def get_async_pool():
    """Get the asynchronous database pool"""
    pool = await db_manager.init_async_pool()
    if not pool:
        raise Exception("Asynchronous database pool not available")
    
    # Ensure schema is initialized
    await db_manager.ensure_tables_exist()
    
    return pool

def init_database():
    """Initialize the database (can be called explicitly)"""
    return db_manager.init_db()

def start_temp_table_cleanup():
    """Start the temp table cleanup thread"""
    db_manager.start_cleanup_thread()

# For testing
if __name__ == "__main__":
    print("Testing database manager...")
    success = init_database()
    print(f"Database initialization: {'Success' if success else 'Failed'}")
    
    # Test sync connection
    try:
        conn = get_sync_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        print(f"Sync connection test: {result}")
        cur.close()
        release_sync_connection(conn)
    except Exception as e:
        print(f"Sync connection test failed: {e}")
    
    # Test async connection
    async def test_async():
        try:
            pool = await get_async_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                print(f"Async connection test: {result}")
        except Exception as e:
            print(f"Async connection test failed: {e}")
    
    asyncio.run(test_async())
    
    print("Database manager test complete")