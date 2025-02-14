import time
from typing import Optional, Dict, Any
from config import Config

class Session:
    def __init__(self, user: Dict[str, Any]):
        if not isinstance(user, dict):
            raise TypeError("User must be a dictionary")
        if not user:
            raise ValueError("User dictionary cannot be empty")
        if "id" not in user:
            raise ValueError("User dictionary must contain 'id' key")
            
        self.user = user.copy()  # Create a copy to prevent external modifications
        try:
            self.start_time = time.time()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize session time: {e}")
    
    def is_valid(self) -> bool:
        """Check if session is valid"""
        if not hasattr(self, 'start_time'):
            return False
            
        try:
            current_time = time.time()
            return (current_time - self.start_time) < Config.SESSION_TIMEOUT
        except Exception:
            return False
    
    def refresh(self) -> None:
        """Refresh session timestamp"""
        try:
            self.start_time = time.time()
        except Exception as e:
            raise RuntimeError(f"Failed to refresh session time: {e}")
    
    def get_user(self) -> Dict[str, Any]:
        """Get user information"""
        if not hasattr(self, 'user'):
            raise RuntimeError("User information not initialized")
        return self.user.copy()  # Return a copy to prevent external modifications
