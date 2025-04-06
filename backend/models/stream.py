from pydantic import BaseModel
from typing import Dict, Optional

class SensorData(BaseModel):
    device_id: str
    sensor_data: Dict

class TrialResponse(BaseModel):
    trial_id: int
    status: str
    data_file: Optional[str] = None
    readings: Optional[int] = None
