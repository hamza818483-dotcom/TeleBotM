"""
Concurrency management for multi-user support.
Handles rate limiting, queue management, and task scheduling per user.
"""

import asyncio
from typing import Dict, Optional, Callable, Any
from collections import defaultdict
from datetime import datetime, timedelta


class UserConcurrencyManager:
    """
    Manages concurrent operations per user.
    Prevents race conditions and ensures fair resource allocation.
    """
    
    def __init__(self, max_concurrent_per_user: int = 1, rate_limit_window_seconds: int = 60):
        self.max_concurrent_per_user = max_concurrent_per_user
        self.rate_limit_window_seconds = rate_limit_window_seconds
        
        # Per-user locks for critical operations
        self._user_locks: Dict[int, asyncio.Lock] = {}
        
        # Per-user semaphores for concurrent operations
        self._user_semaphores: Dict[int, asyncio.Semaphore] = {}
        
        # Per-user operation queues
        self._user_queues: Dict[int, asyncio.Queue] = {}
        
        # Rate limiting: track operations per user
        self._user_operations: Dict[int, list] = defaultdict(list)
        
        # Active tasks per user
        self._user_tasks: Dict[int, set] = defaultdict(set)
    
    def _get_user_lock(self, user_id: int) -> asyncio.Lock:
        """Get or create a lock for a user."""
        if user_id not in self._user_locks:
            self._user_locks[user_id] = asyncio.Lock()
        return self._user_locks[user_id]
    
    def _get_user_semaphore(self, user_id: int) -> asyncio.Semaphore:
        """Get or create a semaphore for a user."""
        if user_id not in self._user_semaphores:
            self._user_semaphores[user_id] = asyncio.Semaphore(self.max_concurrent_per_user)
        return self._user_semaphores[user_id]
    
    async def acquire_user_lock(self, user_id: int):
        """Acquire exclusive lock for a user."""
        return self._get_user_lock(user_id)
    
    async def with_user_lock(self, user_id: int, coro):
        """Execute coroutine with user lock."""
        async with self._get_user_lock(user_id):
            return await coro
    
    async def with_user_semaphore(self, user_id: int, coro):
        """Execute coroutine with user semaphore (allows concurrent operations)."""
        async with self._get_user_semaphore(user_id):
            return await coro
    
    def track_operation(self, user_id: int) -> None:
        """Track an operation for rate limiting."""
        now = datetime.utcnow()
        # Remove old operations outside the window
        self._user_operations[user_id] = [
            op_time for op_time in self._user_operations[user_id]
            if (now - op_time).total_seconds() < self.rate_limit_window_seconds
        ]
        # Add new operation
        self._user_operations[user_id].append(now)
    
    def get_operation_count(self, user_id: int) -> int:
        """Get number of operations in current rate limit window."""
        self.track_operation(user_id)  # Clean up old ops
        return len(self._user_operations[user_id])
    
    def is_rate_limited(self, user_id: int, max_ops: int = 10) -> bool:
        """Check if user is rate limited."""
        return self.get_operation_count(user_id) > max_ops
    
    async def wait_if_rate_limited(self, user_id: int, max_ops: int = 10) -> None:
        """Wait if user is rate limited."""
        while self.is_rate_limited(user_id, max_ops):
            await asyncio.sleep(0.5)
        self.track_operation(user_id)
    
    def register_task(self, user_id: int, task: asyncio.Task) -> None:
        """Register an active task for a user."""
        self._user_tasks[user_id].add(task)
        task.add_done_callback(lambda t: self._user_tasks[user_id].discard(t))
    
    def get_active_task_count(self, user_id: int) -> int:
        """Get number of active tasks for a user."""
        return len(self._user_tasks[user_id])
    
    async def wait_for_user_idle(self, user_id: int, timeout: float = 30.0) -> bool:
        """Wait for user to have no active tasks."""
        start = datetime.utcnow()
        while self.get_active_task_count(user_id) > 0:
            if (datetime.utcnow() - start).total_seconds() > timeout:
                return False
            await asyncio.sleep(0.1)
        return True
    
    def get_user_status(self, user_id: int) -> Dict[str, Any]:
        """Get concurrency status for a user."""
        return {
            'user_id': user_id,
            'active_tasks': self.get_active_task_count(user_id),
            'operations_in_window': self.get_operation_count(user_id),
            'is_rate_limited': self.is_rate_limited(user_id),
        }
    
    async def cleanup_user(self, user_id: int) -> None:
        """Clean up all state for a user."""
        # Cancel active tasks
        for task in list(self._user_tasks[user_id]):
            if not task.done():
                task.cancel()
        # Remove state
        self._user_locks.pop(user_id, None)
        self._user_semaphores.pop(user_id, None)
        self._user_tasks.pop(user_id, None)
        self._user_operations.pop(user_id, None)


# Global singleton instance
concurrency_manager = UserConcurrencyManager(max_concurrent_per_user=2)
