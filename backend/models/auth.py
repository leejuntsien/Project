from pydantic import BaseModel
from typing import Optional

class TokenData(BaseModel):
    sub: str  # device_id
    patient_id: int
    exp: Optional[int] = None

class DeviceAuth(BaseModel):
    device_id: str
    secret: str
