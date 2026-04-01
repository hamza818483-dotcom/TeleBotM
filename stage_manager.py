"""
Stage manager for coordinating per-user request queues.

Allows multiple users to run expensive operations at the same time while
queueing consecutive requests from the same user. Each user gets a dedicated
queue processed sequentially, and a global semaphore limits the total number of
tasks executing simultaneously to avoid resource exhaustion.
"""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Dict, Optional, Tuple, Any


class StageType(Enum):
    """High level categories for staged work."""

    IMAGE_TO_QUIZ = "image_to_quiz"
    PDF_PROCESS = "pdf_process"
    MEDIA_GROUP = "media_group"
    CUSTOM_PROMPT = "custom_prompt"
    EXPORT = "export"
    DEFAULT = "default"


@dataclass
class StageJob:
    """Represents a queued job."""

    stage_type: StageType
    coro_factory: Callable[[], Awaitable[Any]]
    future: asyncio.Future
    enqueued_at: float


class StageTimeoutError(Exception):
    """Raised when a staged job exceeds its allotted time."""


class StageManager:
    """Coordinates per-user queues with a global concurrency cap."""

    def __init__(self) -> None:
        try:
            max_workers = int(os.getenv("MAX_STAGE_WORKERS", "8"))
        except ValueError:
            max_workers = 8
        self._max_workers = max(1, max_workers)
        self._global_semaphore = asyncio.Semaphore(self._max_workers)
        self._queues: Dict[str, asyncio.Queue[StageJob]] = {}
        self._workers: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._idle_timeout = int(os.getenv("STAGE_WORKER_IDLE_TIMEOUT", "30"))
        self._default_timeout = int(os.getenv("STAGE_TIMEOUT_DEFAULT", "1800"))
        self._stage_timeouts = self._load_stage_timeouts()

    def _load_stage_timeouts(self) -> Dict[StageType, int]:
        """Load optional per-stage timeouts from environment variables."""
        timeouts: Dict[StageType, int] = {}
        for stage in StageType:
            env_key = f"STAGE_TIMEOUT_{stage.name}"
            value = os.getenv(env_key)
            if value is None:
                continue
            try:
                timeout_val = max(0, int(value))
                timeouts[stage] = timeout_val
            except ValueError:
                continue
        return timeouts

    async def run(
        self,
        user_id: str,
        stage_type: StageType,
        coro_factory: Callable[[], Awaitable[Any]],
        on_queue: Optional[Callable[[int], Awaitable[None]]] = None,
    ) -> Any:
        """
        Queue a coroutine factory for the given user and wait for the result.

        Args:
            user_id: Telegram user id as string.
            stage_type: Category for logging/metrics.
            coro_factory: Callable returning the coroutine to run.
            on_queue: Optional coroutine called with the number of jobs ahead when
                the request is queued (only when position > 0).
        """

        queue = await self._get_or_create_queue(user_id)
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        job = StageJob(stage_type=stage_type, coro_factory=coro_factory, future=future, enqueued_at=time.time())
        await queue.put(job)

        queue_size = queue.qsize()
        if on_queue and queue_size > 1:
            # queue_size includes the current job, so subtract 1 for jobs ahead
            try:
                await on_queue(queue_size - 1)
            except Exception:
                # Avoid breaking queue because notification failed
                pass

        await self._ensure_worker(user_id)
        return await future

    async def get_user_queue_size(self, user_id: str) -> int:
        """Return the current queued job count for a user (excluding active job)."""
        queue = self._queues.get(user_id)
        if not queue:
            return 0
        size = queue.qsize()
        return max(0, size - 1 if any(worker_user == user_id for worker_user in self._workers.keys()) else size)

    async def get_stats(self) -> Dict[str, Any]:
        """Return current statistics for debugging."""
        async with self._lock:
            return {
                "active_workers": len(self._workers),
                "tracked_users": len(self._queues),
                "max_workers": self._max_workers,
            }

    async def _get_or_create_queue(self, user_id: str) -> asyncio.Queue:
        async with self._lock:
            if user_id not in self._queues:
                self._queues[user_id] = asyncio.Queue()
            return self._queues[user_id]

    async def _ensure_worker(self, user_id: str) -> None:
        async with self._lock:
            worker = self._workers.get(user_id)
            if worker and not worker.done():
                return
            queue = self._queues.get(user_id)
            if queue is None:
                return
            self._workers[user_id] = asyncio.create_task(self._user_worker(user_id, queue))

    async def _user_worker(self, user_id: str, queue: asyncio.Queue) -> None:
        """Continuously process jobs for a specific user until idle."""
        try:
            while True:
                try:
                    job: StageJob = await asyncio.wait_for(queue.get(), timeout=self._idle_timeout)
                except asyncio.TimeoutError:
                    if queue.empty():
                        break
                    continue

                try:
                    async with self._global_semaphore:
                        timeout = self._stage_timeouts.get(job.stage_type, self._default_timeout)
                        try:
                            if timeout > 0:
                                result = await asyncio.wait_for(job.coro_factory(), timeout=timeout)
                            else:
                                result = await job.coro_factory()
                        except asyncio.TimeoutError as exc:
                            raise StageTimeoutError(
                                f"Stage job {job.stage_type.value} exceeded timeout of {timeout}s"
                            ) from exc
                    if not job.future.cancelled():
                        job.future.set_result(result)
                except Exception as exc:  # pylint: disable=broad-except
                    if not job.future.cancelled():
                        job.future.set_exception(exc)
                finally:
                    queue.task_done()
        finally:
            async with self._lock:
                self._workers.pop(user_id, None)
                if queue.empty():
                    self._queues.pop(user_id, None)


# Global instance
stage_manager = StageManager()

