
import streamlit as st
from functools import wraps
import time

def prevent_rerun(key, timeout=2):
    """Prevents a function from being rerun too frequently
    
    Args:
        key (str): A unique key for this function
        timeout (int): Minimum seconds between runs
    
    Returns:
        function: Decorator that prevents frequent reruns
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_run_key = f"last_run_{key}"
            current_time = time.time()
            
            if last_run_key not in st.session_state:
                st.session_state[last_run_key] = 0
                
            time_since_last_run = current_time - st.session_state[last_run_key]
            
            if time_since_last_run < timeout:
                return None
                
            st.session_state[last_run_key] = current_time
            return func(*args, **kwargs)
        return wrapper
    return decorator

def cached_data(key, func, *args, ttl=300, **kwargs):
    """Caches the result of a function call in session state
    
    Args:
        key (str): Key to store the result
        func (callable): Function to call
        ttl (int): Time to live in seconds
        *args, **kwargs: Arguments to pass to func
    
    Returns:
        Any: The cached or new result
    """
    cache_key = f"cache_{key}"
    timestamp_key = f"timestamp_{key}"
    current_time = time.time()
    
    # Check if we have cached data and if it's still valid
    if (cache_key in st.session_state and 
        timestamp_key in st.session_state and 
        current_time - st.session_state[timestamp_key] < ttl):
        return st.session_state[cache_key]
    
    # Otherwise call the function and cache the result
    result = func(*args, **kwargs)
    st.session_state[cache_key] = result
    st.session_state[timestamp_key] = current_time
    return result

def lazy_load(show_spinner=True):
    """Decorator to lazily load data only when needed
    
    Args:
        show_spinner (bool): Whether to show a spinner
    
    Returns:
        function: Decorator for lazy loading
    """
    def decorator(func):
        result_key = f"lazy_result_{func.__name__}"
        loaded_key = f"lazy_loaded_{func.__name__}"
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            if loaded_key not in st.session_state:
                st.session_state[loaded_key] = False
                
            if not st.session_state[loaded_key]:
                if show_spinner:
                    with st.spinner("Loading data..."):
                        result = func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                    
                st.session_state[result_key] = result
                st.session_state[loaded_key] = True
                
            return st.session_state[result_key]
        
        return wrapper
    return decorator

def page_reloader(seconds=60):
    """Adds a countdown timer that will reload the page
    
    Args:
        seconds (int): Seconds between reloads
    """
    if 'reload_time' not in st.session_state:
        st.session_state.reload_time = time.time() + seconds
        
    time_left = max(0, int(st.session_state.reload_time - time.time()))
    
    # Update the reload time if it's expired
    if time_left <= 0:
        st.session_state.reload_time = time.time() + seconds
        st.rerun()
        
    # Display remaining time (small and unobtrusive)
    st.markdown(f"""
    <div style="position: fixed; bottom: 10px; right: 10px; 
                background-color: rgba(59, 130, 246, 0.1); 
                padding: 5px 10px; border-radius: 5px; 
                font-size: 12px; color: #3b82f6;">
        Auto-refresh: {time_left}s
    </div>
    """, unsafe_allow_html=True)

class StatefulButton:
    """A button that retains its state between reruns"""
    
    def __init__(self, label, key=None, type="primary"):
        """Initialize the stateful button
        
        Args:
            label (str): Button label
            key (str): Unique key for the button
            type (str): Button type (primary, secondary, danger, etc.)
        """
        self.label = label
        self.key = key or label.lower().replace(" ", "_")
        self.type = type
        self.state_key = f"btn_state_{self.key}"
        
        # Initialize state if needed
        if self.state_key not in st.session_state:
            st.session_state[self.state_key] = False
    
    def clicked(self):
        """Check if the button has been clicked
        
        Returns:
            bool: True if the button was clicked
        """
        # Get previous state
        was_clicked = st.session_state[self.state_key]
        
        # Reset the state
        if was_clicked:
            st.session_state[self.state_key] = False
            
        return was_clicked
    
    def render(self):
        """Render the button
        
        Returns:
            bool: True if the button is clicked
        """
        from utils.admin_ui import format_button
        
        if format_button(self.label, key=self.key, type=self.type):
            st.session_state[self.state_key] = True
            return True
        return False

def ajax_button(label, func, *args, key=None, type="primary", **kwargs):
    """Create a button that runs a function without refreshing the page
    
    Args:
        label (str): Button label
        func (callable): Function to call when clicked
        *args, **kwargs: Arguments to pass to func
        key (str): Unique key for the button
        type (str): Button type (primary, secondary, danger, etc.)
    
    Returns:
        bool: True if the function was successfully called
    """
    key = key or f"ajax_{label.lower().replace(' ', '_')}"
    result_key = f"ajax_result_{key}"
    
    clicked = StatefulButton(label, key, type).render()
    
    if clicked:
        try:
            result = func(*args, **kwargs)
            st.session_state[result_key] = result
            return True
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return False
    
    return False

