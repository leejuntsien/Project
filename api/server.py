from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_socketio import SocketIO, emit
from datetime import timedelta
import os
import sys
import json
from datetime import datetime
import logging

# Add the parent directory to the path so we can import the database manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import get_sync_connection, release_sync_connection, init_database, start_temp_table_cleanup
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('flask_server')

# Load environment variables from the correct path
env_path = os.path.join('.env', 'FYP_webapp.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    logger.info(f"Loaded environment variables from {env_path}")
else:
    logger.warning(f"Environment file not found at {env_path}")
    # Try alternative locations as fallback
    if os.path.exists('.env'):
        load_dotenv('.env')
        logger.info("Loaded environment variables from .env")
    elif os.path.exists('../.env'):
        load_dotenv('../.env')
        logger.info("Loaded environment variables from ../.env")
    else:
        logger.warning("No .env file found. Using default or system environment variables.")


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
if not JWT_SECRET_KEY:
    logger.warning("JWT_SECRET_KEY not found. Using a default value for development.")
    JWT_SECRET_KEY = 'dev-secret-key'  # Only for development!

app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
jwt = JWTManager(app)

# Initialize the database when the server starts
init_database()

# Start the temp table cleanup thread
start_temp_table_cleanup()

# Device authentication
DEVICE_SECRET = os.getenv('DEVICE_SECRET')
if not DEVICE_SECRET:
    logger.warning("DEVICE_SECRET not found. Using a default value for development.")
    DEVICE_SECRET = 'dev-device-secret'  # Only for development!

authenticated_devices = set()

@app.route('/api/device/auth', methods=['POST'])
def device_auth():
    data = request.get_json()
    if not data or 'device_id' not in data or 'secret' not in data:
        return jsonify({'error': 'Missing credentials'}), 400
    
    if data['secret'] != DEVICE_SECRET:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    authenticated_devices.add(data['device_id'])
    token = create_access_token(identity=data['device_id'])
    return jsonify({'token': token}), 200

@app.route('/api/data/stream', methods=['POST'])
@jwt_required()
def receive_data():
    device_id = get_jwt_identity()
    if device_id not in authenticated_devices:
        return jsonify({'error': 'Device not authenticated'}), 401
    
    data = request.get_json()
    if not data or 'patient_id' not in data or 'sensor_data' not in data:
        return jsonify({'error': 'Invalid data format'}), 400
    
    conn = None
    try:
        conn = get_sync_connection()
        cur = conn.cursor()
        
        # Insert data into rolling table
        cur.execute("""
            INSERT INTO sensor_data (patient_id, device_id, sensor_data, timestamp)
            VALUES (%s, %s, %s, %s)
        """, (data['patient_id'], device_id, json.dumps(data['sensor_data']), datetime.now()))
        
        conn.commit()
        cur.close()
        
        # Emit data to connected clients
        socketio.emit('new_data', {
            'patient_id': data['patient_id'],
            'device_id': device_id,
            'sensor_data': data['sensor_data'],
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in receive_data: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            release_sync_connection(conn)

@app.route('/api/devices', methods=['GET'])
@jwt_required()
def get_devices():
    return jsonify({'devices': list(authenticated_devices)}), 200

# Health check endpoint for testing
@app.route('/api/health', methods=['GET'])
def health_check():
    status = {
        'status': 'ok',
        'database': 'connected'
    }
    
    # Test database connection
    try:
        conn = get_sync_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        release_sync_connection(conn)
    except Exception as e:
        status['status'] = 'error'
        status['database'] = f'error: {str(e)}'
    
    return jsonify(status)

if __name__ == '__main__':
    # Print registered routes for debugging
    logger.info("Registered Routes:")
    for rule in app.url_map.iter_rules():
        logger.info(f"{rule.endpoint}: {rule.rule}")
    
    # Start the server
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
