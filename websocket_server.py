from fastapi import FastAPI, WebSocket, HTTPException
from typing import Dict
import json
import asyncpg
from datetime import datetime
import os
import sys
import asyncio
import logging

# Add the parent directory to the path so we can import the database manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import get_async_pool, start_temp_table_cleanup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('websocket_server')

app = FastAPI()

# Store active connections
active_connections: Dict[int, WebSocket] = {}

@app.websocket("/ws/stream/{patient_id}")
async def websocket_endpoint(websocket: WebSocket, patient_id: int):
    await websocket.accept()
    active_connections[patient_id] = websocket
    
    try:
        # Get the database pool (this will auto-initialize the database if needed)
        pool = await get_async_pool()
        
        # Test the connection
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            logger.info(f"Database connection test successful for patient_id: {patient_id}")
        
        await websocket.send_json({"status": "connected", "message": "WebSocket connection established"})
        
        while True:
            # Receive data from client
            data = await websocket.receive_json()
            
            # Validate data format
            if not isinstance(data, dict) or "sensor_data" not in data:
                await websocket.send_json({"error": "Invalid data format"})
                continue
            
            try:
                async with pool.acquire() as conn:
                    # Always insert into live_patient_data (rolling data)
                    try:
                        await conn.execute("""
                            INSERT INTO live_patient_data (patient_id, sensor_data)
                            VALUES ($1, $2::jsonb)
                        """, patient_id, json.dumps(data["sensor_data"]))
                    except asyncpg.UndefinedTableError:
                        logger.warning("live_patient_data table not found. This should not happen with auto-initialization.")
                        await websocket.send_json({"error": "Database tables not properly initialized"})
                        continue
                    
                    # Check if there's an active trial
                    trial_id = None
                    try:
                        trial_result = await conn.fetchrow("""
                            SELECT trial_id 
                            FROM patient_trials 
                            WHERE patient_id = $1 
                            AND end_time IS NULL
                            ORDER BY start_time DESC 
                            LIMIT 1
                        """, patient_id)
                        
                        if trial_result:
                            trial_id = trial_result['trial_id']
                            
                            # If there's an active trial, also insert into trial_temp
                            await conn.execute("""
                                INSERT INTO trial_temp (trial_id, patient_id, sensor_data)
                                VALUES ($1, $2, $3::jsonb)
                            """, trial_id, patient_id, json.dumps(data["sensor_data"]))
                    except asyncpg.UndefinedTableError:
                        logger.warning("Required database tables not found. This should not happen with auto-initialization.")
                    
                # Send acknowledgment
                await websocket.send_json({
                    "status": "ok",
                    "trial_id": trial_id,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as db_error:
                logger.error(f"Database operation error for patient {patient_id}: {str(db_error)}")
                await websocket.send_json({
                    "status": "error",
                    "message": f"Database operation failed: {str(db_error)}"
                })
            
    except Exception as e:
        logger.error(f"Error in WebSocket connection for patient {patient_id}: {str(e)}")
        try:
            await websocket.send_json({"status": "error", "message": "Connection error occurred"})
        except:
            pass  # Connection might already be closed
    finally:
        if patient_id in active_connections:
            del active_connections[patient_id]

# Health check endpoint
@app.get("/health")
async def health_check():
    try:
        pool = await get_async_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": f"error: {str(e)}"}

@app.on_event("startup")
async def startup_event():
    """Run when the server starts"""
    logger.info("Starting WebSocket server...")
    # Start the temp table cleanup thread
    start_temp_table_cleanup()
    
    # Pre-initialize the database to avoid delay on first connection
    try:
        pool = await get_async_pool()
        logger.info("Database pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Run when the server shuts down"""
    logger.info("Shutting down WebSocket server...")

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting WebSocket server on port 5000...")
    uvicorn.run(app, host="0.0.0.0", port=5000)
