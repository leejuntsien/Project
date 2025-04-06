import psycopg2
from argon2 import PasswordHasher

ph = PasswordHasher()  # Create Argon2 instance

def hash_password(password):
    return ph.hash(password)  # Securely hash password

def verify_password(stored_hash, password):
    try:
        return ph.verify(stored_hash, password)
    except:
        return False


