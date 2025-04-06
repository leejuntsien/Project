import psycopg2
import json
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
import sys

# Load environment variables
env_path = os.path.join('.env', 'FYP_webapp.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"Loaded environment variables from {env_path}")
else:
    print(f"Warning: Environment file not found at {env_path}")
    # Try alternative locations as fallback
    if os.path.exists('.env'):
        load_dotenv('.env')
        print("Loaded environment variables from .env")
    elif os.path.exists('../.env'):
        load_dotenv('../.env')
        print("Loaded environment variables from ../.env")
    else:
        print("Warning: No .env file found. Using default or system environment variables.")

# Database connection parameters
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "Patient data FYP")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_db_connection():
    """Get a database connection"""
    try:
        # First try with quoted database name (for names with spaces)
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                database=f'"{DB_NAME}"',  # Quote the database name
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT
            )
            print("Connected to database with quoted name.")
            return conn
        except psycopg2.Error as e:
            print(f"First connection attempt failed: {e}")
            # Try without quotes
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT
            )
            print("Connected to database without quotes.")
            return conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        return None

def inspect_table_schema(table_name):
    """Inspect the schema of a table"""
    conn = get_db_connection()
    if not conn:
        print(f"Could not connect to database to inspect {table_name}")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get column information
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            
            columns = cursor.fetchall()
            
            print(f"\n=== Table Schema: {table_name} ===")
            print(f"{'Column Name':<20} {'Data Type':<20} {'Nullable':<10}")
            print("-" * 50)
            
            for col_name, data_type, is_nullable in columns:
                print(f"{col_name:<20} {data_type:<20} {is_nullable:<10}")
    except Exception as e:
        print(f"Error inspecting schema for {table_name}: {e}")
    finally:
        conn.close()

def inspect_sample_data(table_name, patient_id=None):
    """Inspect sample data from a table"""
    conn = get_db_connection()
    if not conn:
        print(f"Could not connect to database to inspect data in {table_name}")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get a sample row
            if patient_id and 'patient_id' in get_table_columns(table_name):
                cursor.execute(f"""
                    SELECT * FROM {table_name}
                    WHERE patient_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                """, (patient_id,))
            else:
                cursor.execute(f"""
                    SELECT * FROM {table_name}
                    ORDER BY id DESC
                    LIMIT 1
                """)
            
            row = cursor.fetchone()
            
            if not row:
                print(f"\nNo data found in {table_name}")
                return
            
            # Get column names
            cursor.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            
            columns = [col[0] for col in cursor.fetchall()]
            
            print(f"\n=== Sample Data: {table_name} ===")
            for i, col in enumerate(columns):
                value = row[i]
                value_type = type(value).__name__
                
                # For JSON/JSONB columns, try to parse and show structure
                if col == 'sensor_data' and value:
                    if isinstance(value, str):
                        try:
                            parsed = json.loads(value)
                            print(f"{col} (parsed from string):")
                            print(f"  Type: {value_type}")
                            print(f"  Keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'Not a dictionary'}")
                            print(f"  Sample values: {list(parsed.values())[:3] if isinstance(parsed, dict) else parsed[:100]}")
                        except json.JSONDecodeError:
                            print(f"{col}:")
                            print(f"  Type: {value_type}")
                            print(f"  Value: {value[:100]}... (truncated)")
                    else:
                        print(f"{col}:")
                        print(f"  Type: {value_type}")
                        if isinstance(value, dict):
                            print(f"  Keys: {list(value.keys())}")
                            print(f"  Sample values: {list(value.values())[:3]}")
                        else:
                            print(f"  Value: {str(value)[:100]}... (truncated)")
                else:
                    print(f"{col}:")
                    print(f"  Type: {value_type}")
                    print(f"  Value: {value}")
    except Exception as e:
        print(f"Error inspecting data for {table_name}: {e}")
    finally:
        conn.close()

def get_table_columns(table_name):
    """Get column names for a table"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            
            return [col[0] for col in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting columns for {table_name}: {e}")
        return []
    finally:
        conn.close()

def analyze_json_structure(table_name, json_column, patient_id=None):
    """Analyze the structure of JSON data in a column"""
    conn = get_db_connection()
    if not conn:
        print(f"Could not connect to database to analyze JSON in {table_name}")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get sample JSON data
            if patient_id and 'patient_id' in get_table_columns(table_name):
                cursor.execute(f"""
                    SELECT {json_column} FROM {table_name}
                    WHERE patient_id = %s
                    ORDER BY id DESC
                    LIMIT 10
                """, (patient_id,))
            else:
                cursor.execute(f"""
                    SELECT {json_column} FROM {table_name}
                    ORDER BY id DESC
                    LIMIT 10
                """)
            
            rows = cursor.fetchall()
            
            if not rows:
                print(f"\nNo JSON data found in {table_name}.{json_column}")
                return
            
            print(f"\n=== JSON Structure Analysis: {table_name}.{json_column} ===")
            
            # Analyze each JSON object
            all_keys = set()
            value_types = {}
            
            for row in rows:
                json_data = row[0]
                
                # Parse JSON if it's a string
                if isinstance(json_data, str):
                    try:
                        json_data = json.loads(json_data)
                    except json.JSONDecodeError:
                        print(f"Warning: Invalid JSON data: {json_data[:100]}... (truncated)")
                        continue
                
                if not isinstance(json_data, dict):
                    print(f"Warning: JSON data is not a dictionary: {type(json_data).__name__}")
                    continue
                
                # Collect keys and value types
                for key, value in json_data.items():
                    all_keys.add(key)
                    
                    value_type = type(value).__name__
                    if key not in value_types:
                        value_types[key] = set()
                    value_types[key].add(value_type)
            
            # Print summary
            print(f"Found {len(all_keys)} unique keys across {len(rows)} JSON objects")
            print("\nKey analysis:")
            print(f"{'Key':<20} {'Value Types':<30} {'Example Value'}")
            print("-" * 70)
            
            # Get an example value for each key
            for key in sorted(all_keys):
                types_str = ", ".join(sorted(value_types.get(key, ["unknown"])))
                
                # Find an example value
                example = "N/A"
                for row in rows:
                    json_data = row[0]
                    if isinstance(json_data, str):
                        try:
                            json_data = json.loads(json_data)
                        except:
                            continue
                    
                    if isinstance(json_data, dict) and key in json_data:
                        example = str(json_data[key])[:30]
                        if len(example) == 30:
                            example += "..."
                        break
                
                print(f"{key:<20} {types_str:<30} {example}")
    except Exception as e:
        print(f"Error analyzing JSON in {table_name}.{json_column}: {e}")
    finally:
        conn.close()

def test_data_conversion():
    """Test data conversion from database to DataFrame"""
    conn = get_db_connection()
    if not conn:
        print("Could not connect to database for conversion test")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get sample data from live_patient_data
            cursor.execute("""
                SELECT sensor_data, timestamp 
                FROM live_patient_data 
                ORDER BY timestamp DESC 
                LIMIT 10
            """)
            rows = cursor.fetchall()
            
            if not rows:
                print("\nNo data found in live_patient_data for conversion test")
                return
            
            print("\n=== Data Conversion Test ===")
            
            # Method 1: Direct conversion (problematic)
            print("\nMethod 1: Direct conversion (may cause issues)")
            try:
                data = []
                for row in rows:
                    sensor_data, timestamp = row
                    
                    # Parse JSON if needed
                    if isinstance(sensor_data, str):
                        try:
                            sensor_data = json.loads(sensor_data)
                        except:
                            sensor_data = {}
                    
                    # Create entry
                    entry = {"timestamp": timestamp}
                    if isinstance(sensor_data, dict):
                        entry.update(sensor_data)
                    
                    data.append(entry)
                
                df1 = pd.DataFrame(data)
                print(f"DataFrame shape: {df1.shape}")
                print("Column dtypes:")
                for col, dtype in df1.dtypes.items():
                    print(f"  {col}: {dtype}")
                
                # Try to convert to Arrow (this might fail)
                try:
                    import pyarrow as pa
                    table = pa.Table.from_pandas(df1)
                    print("Successfully converted to Arrow table!")
                except Exception as e:
                    print(f"Arrow conversion failed: {e}")
            except Exception as e:
                print(f"Method 1 failed: {e}")
            
            # Method 2: Improved conversion (our fix)
            print("\nMethod 2: Improved conversion with explicit types")
            try:
                # Create separate lists for each column
                timestamps = []
                sensor_values = {}
                
                for row in rows:
                    sensor_data, timestamp = row
                    
                    # Convert timestamp to datetime
                    if isinstance(timestamp, datetime):
                        timestamps.append(timestamp)
                    else:
                        try:
                            timestamps.append(pd.to_datetime(timestamp))
                        except:
                            continue
                    
                    # Parse sensor_data
                    if isinstance(sensor_data, str):
                        try:
                            sensor_data = json.loads(sensor_data)
                        except:
                            continue
                    
                    # Extract numeric values
                    if isinstance(sensor_data, dict):
                        for key, value in sensor_data.items():
                            try:
                                if isinstance(value, (int, float)):
                                    float_value = float(value)
                                elif isinstance(value, str) and value.replace('.', '', 1).isdigit():
                                    float_value = float(value)
                                else:
                                    continue
                                    
                                if key not in sensor_values:
                                    sensor_values[key] = [None] * len(timestamps)
                                
                                while len(sensor_values[key]) < len(timestamps):
                                    sensor_values[key].append(None)
                                
                                sensor_values[key][-1] = float_value
                                
                            except (ValueError, TypeError):
                                pass
                
                # Create DataFrame
                data = {'timestamp': timestamps}
                for key, values in sensor_values.items():
                    while len(values) < len(timestamps):
                        values.append(None)
                    data[key] = values
                
                df2 = pd.DataFrame(data)
                print(f"DataFrame shape: {df2.shape}")
                print("Column dtypes:")
                for col, dtype in df2.dtypes.items():
                    print(f"  {col}: {dtype}")
                
                # Try to convert to Arrow
                try:
                    import pyarrow as pa
                    table = pa.Table.from_pandas(df2)
                    print("Successfully converted to Arrow table!")
                except Exception as e:
                    print(f"Arrow conversion failed: {e}")
            except Exception as e:
                print(f"Method 2 failed: {e}")
    except Exception as e:
        print(f"Error in conversion test: {e}")
    finally:
        conn.close()

def main():
    print("=== Database Table Data Type Debugger ===")
    
    # Inspect table schemas
    tables = ['live_patient_data', 'trial_temp', 'patient_data', 'patient_trials']
    for table in tables:
        inspect_table_schema(table)
    
    # Inspect sample data
    for table in tables:
        inspect_sample_data(table)
    
    # Analyze JSON structure
    analyze_json_structure('live_patient_data', 'sensor_data')
    analyze_json_structure('trial_temp', 'sensor_data')
    
    # Test data conversion
    test_data_conversion()

if __name__ == "__main__":
    main()