import time
from typing import Optional, Dict, Any
from config import Config

class Session:
    def __init__(self, user: Dict[str, Any]):
        self.user = user
        self.start_time = time.time()
    
    def is_valid(self) -> bool:
        """Check if session is valid"""
        current_time = time.time()
        return (current_time - self.start_time) < Config.SESSION_TIMEOUT
    
    def refresh(self) -> None:
        """Refresh session timestamp"""
        self.start_time = time.time()
    
    def get_user(self) -> Dict[str, Any]:
        """Get user information"""
        return self.user
