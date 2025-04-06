import psycopg2
from datetime import datetime, timedelta
import json 
import random
import time
from backend_auth import get_db_connection

def generate_sensor_data():
    """Generate realistic sensor data"""
    return {
        "heart_rate": random.randint(60, 100),
        "temperature": round(random.uniform(35.5, 37.5), 1)
    }

def inject_live_data(patient_id, duration_seconds=60):
    """Inject live data for a specific duration"""
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database")
        return

    try:
        cursor = conn.cursor()
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < duration_seconds:
            data = generate_sensor_data()
            
            # Insert into live_patient_data
            cursor.execute("""
                INSERT INTO live_patient_data (patient_id, heart_rate, temperature)
                VALUES (%s, %s, %s)
            """, (patient_id, data["heart_rate"], data["temperature"]))
            
            conn.commit()
            print(f"Inserted live data for patient {patient_id}: {data}")
            time.sleep(1)  # Wait 1 second between readings
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        conn.close()

def simulate_trial(patient_id):
    """Simulate a complete trial"""
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database")
        return

    try:
        cursor = conn.cursor()
        
        # Start trial
        cursor.execute("""
            INSERT INTO patient_trials (patient_id, start_time)
            VALUES (%s, NOW())
            RETURNING trial_id
        """, (patient_id,))
        trial_id = cursor.fetchone()[0]
        conn.commit()
        
        print(f"Started trial {trial_id} for patient {patient_id}")
        
        # Generate trial data
        trial_data = []
        current_time = datetime.now()
        
        for _ in range(60):  # 1 minute of data
            data = generate_sensor_data()
            data["timestamp"] = current_time.isoformat()
            trial_data.append(data)
            current_time += timedelta(seconds=1)
        
        # Save trial data
        cursor.execute("""
            INSERT INTO patient_data (trial_id, patient_id, processed_data)
            VALUES (%s, %s, %s)
        """, (trial_id, patient_id, json.dumps(trial_data)))
        
        # End trial
        cursor.execute("""
            UPDATE patient_trials 
            SET end_time = NOW()
            WHERE trial_id = %s
        """, (trial_id,))
        
        conn.commit()
        print(f"Completed trial {trial_id} with {len(trial_data)} readings")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Get all patients
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients")
    patients = cursor.fetchall()
    conn.close()

    # Ask what type of data to inject
    print("\nWhat would you like to do?")
    print("1. Inject live data")
    print("2. Simulate complete trials")
    choice = input("Enter your choice (1 or 2): ")

    if choice == "1":
        patient_id = int(input("Enter patient ID (or 0 for all patients): "))
        duration = int(input("Enter duration in seconds: "))
        
        if patient_id == 0:
            for (pid,) in patients:
                print(f"\nInjecting live data for patient {pid}")
                inject_live_data(pid, duration)
        else:
            inject_live_data(patient_id, duration)
            
    elif choice == "2":
        patient_id = int(input("Enter patient ID (or 0 for all patients): "))
        
        if patient_id == 0:
            for (pid,) in patients:
                print(f"\nSimulating trial for patient {pid}")
                simulate_trial(pid)
        else:
            simulate_trial(patient_id)
    
    print("\n✅ Data injection completed!")