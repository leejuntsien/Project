from functools import wraps
import streamlit as st
from datetime import datetime, timedelta
import time
from .jwt_auth import verify_token

def rate_limit(max_requests: int = 5, window_seconds: int = 60):
    def decorator(func):
        requests = []
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            
            # Remove old requests
            while requests and requests[0] < now - window_seconds:
                requests.pop(0)
            
            if len(requests) >= max_requests:
                st.error("Too many attempts. Please try again later.")
                return None
                
            requests.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def require_jwt(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = st.session_state.get('jwt_token')
        if not token:
            st.error("Authentication required")
            return None
            
        payload = verify_token(token)
        if not payload:
            st.error("Invalid or expired token")
            return None
            
        return func(*args, **kwargs)
    return wrapper

def sanitize_input(value: str) -> str:
    """Basic input sanitization"""
    if not isinstance(value, str):
        return ""
    # Remove dangerous characters
    dangerous_chars = ["'", '"', ';', '-', '\\', '/', '*']
    for char in dangerous_chars:
        value = value.replace(char, '')
    return value.strip()
