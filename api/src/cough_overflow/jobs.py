"""Jobs Module."""

from abc import ABC, abstractmethod
from uuid import UUID

from pydantic import Base64Bytes

from cough_overflow.config import CONFIG
from cough_overflow.models import CoughOverflowBase
from redis.asyncio import Redis


class AnalysisJob(CoughOverflowBase):
    """Analysis job to be added to task queue."""

    request_id: UUID
    raw_image: Base64Bytes


class TaskQueuer(ABC):
    """ABC for task queueing."""

    @abstractmethod
    async def queue_task(self, job: AnalysisJob) -> None:
        """Abstract method for queueing a task.

        :param job: _description_
        :type job: AnalysisJob
        """

    @abstractmethod
    async def dequeue_task(self) -> AnalysisJob | None:
        """Abstract method for dequeueing a task.

        :return: Analysis job
        :rtype: AnalysisJob | None
        """


class RedisTaskQueuer(TaskQueuer):
    """Task queuer implementation for redis."""

    QUEUE_NAME = CONFIG.queue_name

    _instance: "RedisTaskQueuer | None" = None  # No singleton mixin - abc no like
    _redis: Redis

    def __init__(self, url: str) -> None:
        """Create redis task queuer."""
        self._redis = Redis.from_url(url)

    async def queue_task(self, job: AnalysisJob) -> None:
        """Queues task."""
        await self._redis.rpush(self.QUEUE_NAME, job.model_dump_json())  # type: ignore[misc] #thanks aioredis type stubs!!!!!

    async def dequeue_task(self) -> AnalysisJob | None:
        """Dequeues task."""
        result: str | None = await self._redis.rpop(self.QUEUE_NAME)  # type: ignore[misc]
        if result is None:
            return None
        return AnalysisJob.model_validate_json(result)

    @classmethod
    def __call__(cls, *args, **kwargs):  # noqa: ANN002, ANN003, ANN206
        """Override call dunder method for singleton."""
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance


def get_queuer() -> TaskQueuer:
    """Get Task Queuer."""
    option = CONFIG.queue_type
    if option == "redis":
        return RedisTaskQueuer(CONFIG.queue_url)

    msg = f"The task_queue config variable is set to '{option}' which does not correlate to a valid task queuer."
    raise ValueError(msg)
