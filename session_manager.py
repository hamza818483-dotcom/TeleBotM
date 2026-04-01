import asyncio
import time
import os
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

class UserSessionStatus(Enum):
    IDLE = "idle"
    PROCESSING_IMAGE = "processing_image"
    PROCESSING_TEXTBOOK = "processing_textbook"
    WAITING_FOR_INPUT = "waiting_for_input"
    ERROR = "error"

@dataclass
class UserSession:
    """Represents a user's current session state"""
    user_id: str
    status: UserSessionStatus
    last_activity: float
    current_batch_id: Optional[str] = None
    processing_start_time: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def is_expired(self, timeout_seconds: int = 300) -> bool:
        """Check if session has expired (5 minutes default)"""
        return time.time() - self.last_activity > timeout_seconds
    
    def is_processing(self) -> bool:
        """Check if user is currently processing something"""
        return self.status in [UserSessionStatus.PROCESSING_IMAGE, UserSessionStatus.PROCESSING_TEXTBOOK]
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()

class UserSessionManager:
    """
    Manages user sessions to prevent conflicts and handle rate limiting.
    """
    
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        self.cleanup_interval = 60  # Cleanup every 60 seconds
        self.session_timeout = 300  # 5 minutes timeout
        # Allow configuration via env var, default higher for better concurrency
        try:
            self.max_concurrent_users = int(os.getenv('MAX_CONCURRENT_USERS', '100'))
        except ValueError:
            self.max_concurrent_users = 100
        self._cleanup_task = None
        self._cleanup_started = False
    
    def _start_cleanup_task(self):
        """Start the cleanup task"""
        if not self._cleanup_started:
            try:
                # Only create task if there's a running event loop
                loop = asyncio.get_running_loop()
                if self._cleanup_task is None or self._cleanup_task.done():
                    self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
                    self._cleanup_started = True
            except RuntimeError:
                # No running loop yet, will be started later
                pass
    
    def start_cleanup_task(self):
        """Start the cleanup task (call this when event loop is running)"""
        self._start_cleanup_task()
    
    async def _cleanup_expired_sessions(self):
        """Cleanup expired sessions periodically"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                current_time = time.time()
                expired_users = []
                
                for user_id, session in self.sessions.items():
                    if session.is_expired(self.session_timeout):
                        expired_users.append(user_id)
                
                for user_id in expired_users:
                    del self.sessions[user_id]
                    print(f"Cleaned up expired session for user {user_id}")
                
                if expired_users:
                    print(f"Cleaned up {len(expired_users)} expired sessions")
                    
            except Exception as e:
                print(f"Error in session cleanup: {str(e)}")
    
    def get_session(self, user_id: str) -> UserSession:
        """Get or create a user session"""
        if user_id not in self.sessions:
            self.sessions[user_id] = UserSession(
                user_id=user_id,
                status=UserSessionStatus.IDLE,
                last_activity=time.time()
            )
        else:
            self.sessions[user_id].update_activity()
        
        return self.sessions[user_id]
    
    def can_process(self, user_id: str) -> tuple[bool, str]:
        """
        Check if user can start processing.
        Returns (can_process, reason)
        """
        session = self.get_session(user_id)
        
        # Check if user is already processing
        if session.is_processing():
            return False, "User is already processing an image"
        
        # Check concurrent user limit
        active_users = sum(1 for s in self.sessions.values() if s.is_processing())
        if active_users >= self.max_concurrent_users:
            return False, f"Too many users processing simultaneously (max: {self.max_concurrent_users})"
        
        # Check retry limit
        if session.retry_count >= session.max_retries:
            return False, "User has exceeded maximum retry attempts"
        
        return True, "OK"
    
    def start_processing(self, user_id: str, status: UserSessionStatus, batch_id: str = None) -> bool:
        """Start processing for a user"""
        session = self.get_session(user_id)
        
        can_process, reason = self.can_process(user_id)
        if not can_process:
            print(f"Cannot start processing for user {user_id}: {reason}")
            return False
        
        session.status = status
        session.processing_start_time = time.time()
        session.current_batch_id = batch_id
        session.update_activity()
        
        print(f"Started {status.value} for user {user_id}")
        return True
    
    def finish_processing(self, user_id: str, success: bool = True):
        """Finish processing for a user"""
        if user_id in self.sessions:
            session = self.sessions[user_id]
            session.status = UserSessionStatus.IDLE if success else UserSessionStatus.ERROR
            session.processing_start_time = None
            session.current_batch_id = None
            
            if not success:
                session.retry_count += 1
            else:
                session.retry_count = 0  # Reset on success
            
            session.update_activity()
            print(f"Finished processing for user {user_id} (success: {success})")
    
    def get_processing_time(self, user_id: str) -> Optional[float]:
        """Get how long a user has been processing"""
        if user_id in self.sessions:
            session = self.sessions[user_id]
            if session.processing_start_time:
                return time.time() - session.processing_start_time
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        total_sessions = len(self.sessions)
        processing_sessions = sum(1 for s in self.sessions.values() if s.is_processing())
        idle_sessions = sum(1 for s in self.sessions.values() if s.status == UserSessionStatus.IDLE)
        error_sessions = sum(1 for s in self.sessions.values() if s.status == UserSessionStatus.ERROR)
        
        return {
            "total_sessions": total_sessions,
            "processing_sessions": processing_sessions,
            "idle_sessions": idle_sessions,
            "error_sessions": error_sessions,
            "max_concurrent_users": self.max_concurrent_users
        }
    
    def cleanup(self):
        """Cleanup the session manager"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

# Global session manager instance
# Will be initialized properly when the event loop is running
_session_manager_instance = None

def get_session_manager():
    """Get or create the session manager instance"""
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = UserSessionManager()
    return _session_manager_instance

# For backward compatibility, create instance but don't start cleanup yet
session_manager = UserSessionManager()
