from datetime import datetime
import json
import os
from typing import Dict, List
import asyncio
from collections import defaultdict
import asyncpg
from fastapi import WebSocket

class StreamService:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.active_trials: Dict[int, Dict] = {}  # patient_id -> trial info
        self.data_buffer: Dict[int, List] = defaultdict(list)
        self.buffer_size = 1000  # Number of readings before batch insert

    async def start_trial(self, patient_id: int, device_id: str) -> int:
        """Start a new trial for a patient"""
        async with self.pool.acquire() as conn:
            trial_id = await conn.fetchval("""
                INSERT INTO patient_trials (patient_id, device_id, start_time)
                VALUES ($1, $2, NOW())
                RETURNING trial_id
            """, patient_id, device_id)
            
            self.active_trials[patient_id] = {
                'trial_id': trial_id,
                'start_time': datetime.now(),
                'device_id': device_id
            }
            return trial_id

    async def end_trial(self, patient_id: int) -> Dict:
        """End a trial and save data to permanent storage"""
        if patient_id not in self.active_trials:
            return {'error': 'No active trial found'}

        trial_info = self.active_trials[patient_id]
        buffer_data = self.data_buffer[patient_id]

        if not buffer_data:
            return {'error': 'No data collected'}

        # Save buffered data to file
        filename = f"trial_{trial_info['trial_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join('data', 'trials', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(buffer_data, f)

        async with self.pool.acquire() as conn:
            # Update trial end time and file path
            await conn.execute("""
                UPDATE patient_trials 
                SET end_time = NOW(), data_file_path = $1
                WHERE trial_id = $2
            """, filepath, trial_info['trial_id'])

            # Process and save to patient_data
            processed_data = self.process_trial_data(buffer_data)
            await conn.execute("""
                INSERT INTO patient_data (trial_id, patient_id, processed_data)
                VALUES ($1, $2, $3)
            """, trial_info['trial_id'], patient_id, json.dumps(processed_data))

        # Clean up
        del self.active_trials[patient_id]
        del self.data_buffer[patient_id]

        return {
            'trial_id': trial_info['trial_id'],
            'data_file': filepath,
            'readings': len(buffer_data)
        }

    async def handle_sensor_data(self, patient_id: int, device_id: str, data: Dict):
        """Handle incoming sensor data"""
        # Only store in temp table if trial is active
        if patient_id in self.active_trials:
            self.data_buffer[patient_id].append({
                'timestamp': datetime.now().isoformat(),
                'data': data
            })

            # Batch insert when buffer is full
            if len(self.data_buffer[patient_id]) >= self.buffer_size:
                await self._batch_insert_temp_data(patient_id)

        # Always store in temp table for live monitoring
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO temp_sensor_data (patient_id, device_id, sensor_data)
                VALUES ($1, $2, $3)
            """, patient_id, device_id, json.dumps(data))

    async def _batch_insert_temp_data(self, patient_id: int):
        """Batch insert buffered data to temp table"""
        if not self.data_buffer[patient_id]:
            return

        async with self.pool.acquire() as conn:
            # Create a prepared statement for better performance
            stmt = await conn.prepare("""
                INSERT INTO temp_sensor_data (patient_id, device_id, sensor_data, timestamp)
                VALUES ($1, $2, $3, $4)
            """)
            
            # Execute batch insert
            await conn.executemany(
                stmt,
                [(
                    patient_id,
                    self.active_trials[patient_id]['device_id'],
                    json.dumps(reading['data']),
                    reading['timestamp']
                ) for reading in self.data_buffer[patient_id]]
            )

        # Clear buffer after successful insert
        self.data_buffer[patient_id] = []

    @staticmethod
    def process_trial_data(buffer_data: List[Dict]) -> Dict:
        """Process trial data for permanent storage"""
        # Implement your data processing logic here
        # This is just a simple example
        return {
            'total_readings': len(buffer_data),
            'start_time': buffer_data[0]['timestamp'],
            'end_time': buffer_data[-1]['timestamp'],
            'data_summary': buffer_data  # You might want to process this further
        }
