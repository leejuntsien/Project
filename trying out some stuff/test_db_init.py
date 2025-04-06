import os
import sys
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_db_init')

# Add the parent directory to the path so we can import the database manager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database.db_manager import init_database, get_sync_connection, release_sync_connection

def test_sync_db():
    """Test synchronous database initialization and table existence"""
    logger.info("Testing synchronous database initialization...")
    
    # Initialize the database
    success = init_database()
    logger.info(f"Database initialization: {'Success' if success else 'Failed'}")
    
    if not success:
        return False
    
    # Check if tables exist
    try:
        conn = get_sync_connection()
        cur = conn.cursor()
        
        # Get list of tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cur.fetchall()]
        
        logger.info(f"Tables in database: {', '.join(tables)}")
        
        # Check for required tables
        required_tables = ['patient_trials', 'live_patient_data', 'trial_temp', 'sensor_data']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            logger.error(f"Missing tables: {', '.join(missing_tables)}")
            return False
        
        # Test querying each table
        for table in required_tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                logger.info(f"Table {table} exists and has {count} rows")
            except Exception as e:
                logger.error(f"Error querying table {table}: {e}")
                return False
        
        cur.close()
        release_sync_connection(conn)
        return True
        
    except Exception as e:
        logger.error(f"Error testing database: {e}")
        return False

async def test_async_db():
    """Test asynchronous database initialization and table existence"""
    logger.info("Testing asynchronous database initialization...")
    
    # Import here to avoid circular imports
    from database.db_manager import get_async_pool
    
    try:
        pool = await get_async_pool()
        
        async with pool.acquire() as conn:
            # Get list of tables
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_names = [row['table_name'] for row in tables]
            
            logger.info(f"Tables in database (async): {', '.join(table_names)}")
            
            # Check for required tables
            required_tables = ['patient_trials', 'live_patient_data', 'trial_temp', 'sensor_data']
            missing_tables = [table for table in required_tables if table not in table_names]
            
            if missing_tables:
                logger.error(f"Missing tables (async): {', '.join(missing_tables)}")
                return False
            
            # Test querying each table
            for table in required_tables:
                try:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    logger.info(f"Table {table} exists and has {count} rows (async)")
                except Exception as e:
                    logger.error(f"Error querying table {table} (async): {e}")
                    return False
            
            return True
            
    except Exception as e:
        logger.error(f"Error testing async database: {e}")
        return False

if __name__ == "__main__":
    # Run synchronous test
    sync_result = test_sync_db()
    
    # Run asynchronous test
    async_result = asyncio.run(test_async_db())
    
    # Print summary
    print("\n=== Test Results ===")
    print(f"Synchronous DB Test: {'PASSED' if sync_result else 'FAILED'}")
    print(f"Asynchronous DB Test: {'PASSED' if async_result else 'FAILED'}")
    
    # Exit with appropriate code
    sys.exit(0 if sync_result and async_result else 1)