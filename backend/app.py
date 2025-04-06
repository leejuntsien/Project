from fastapi import FastAPI, WebSocket, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
import asyncpg
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from services.stream_service import StreamService
from models.auth import TokenData, DeviceAuth
from models.stream import SensorData, TrialResponse
import ssl

load_dotenv()

app = FastAPI(
    title="FYP WebApp API",
    description="Secure API with SSL and CORS protection",
    version="1.0.0"
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# CORS middleware with more restrictive settings
allowed_origins = [
    "https://localhost:8501",  # Streamlit frontend
    "https://localhost:3000",  # Any other frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Database connection pool
async def init_db():
    return await asyncpg.create_pool(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

# Initialize services
pool = None
stream_service = None

@app.on_event("startup")
async def startup_event():
    global pool, stream_service
    pool = await init_db()
    stream_service = StreamService(pool)

@app.on_event("shutdown")
async def shutdown_event():
    if pool:
        await pool.close()

# Authentication endpoints
async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    try:
        payload = jwt.decode(token, os.getenv('JWT_SECRET'), algorithms=["HS256"])
        return TokenData(**payload)
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/token")
async def login(auth_data: DeviceAuth):
    async with pool.acquire() as conn:
        device = await conn.fetchrow(
            "SELECT device_id, patient_id FROM device_auth WHERE device_id = $1 AND secret_hash = $2",
            auth_data.device_id, auth_data.secret
        )
        if not device:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token_data = {
            "sub": device["device_id"],
            "patient_id": device["patient_id"],
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(token_data, os.getenv('JWT_SECRET'), algorithm="HS256")
        return {"access_token": token, "token_type": "bearer"}

# Streaming endpoints
@app.websocket("/ws/stream/{patient_id}")
async def websocket_endpoint(websocket: WebSocket, patient_id: int):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            await stream_service.handle_sensor_data(patient_id, data["device_id"], data["sensor_data"])
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

@app.post("/trial/start/{patient_id}")
async def start_trial(
    patient_id: int,
    current_user: TokenData = Depends(get_current_user)
) -> TrialResponse:
    if current_user.patient_id != patient_id:
        raise HTTPException(status_code=403, detail="Not authorized for this patient")
    
    trial_id = await stream_service.start_trial(patient_id, current_user.sub)
    return {"trial_id": trial_id, "status": "started"}

@app.post("/trial/end/{patient_id}")
async def end_trial(
    patient_id: int,
    current_user: TokenData = Depends(get_current_user)
) -> TrialResponse:
    if current_user.patient_id != patient_id:
        raise HTTPException(status_code=403, detail="Not authorized for this patient")
    
    result = await stream_service.end_trial(patient_id)
    return {"trial_id": result["trial_id"], "status": "completed", **result}

if __name__ == "__main__":
    import uvicorn
    ssl_keyfile = os.path.join(os.path.dirname(__file__), "..", "ssl", "server.key")
    ssl_certfile = os.path.join(os.path.dirname(__file__), "..", "ssl", "server.crt")
    
    if os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile=ssl_certfile, keyfile=ssl_keyfile)
        uvicorn.run(app, host="0.0.0.0", port=5000, ssl=ssl_context)
    else:
        print("Warning: SSL certificates not found. Running without SSL (not recommended for production)")
        uvicorn.run(app, host="0.0.0.0", port=5000)
