"""Main App."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from cough_overflow.api import v1
from cough_overflow.db import initialise_database

# from cough_overflow.config import CONFIG
# from cough_overflow.models import CoughOverflowBase
# from redis.asyncio import Redis


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    """App lifespan."""
    await initialise_database()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(v1.router, prefix="/api/v1")


# class Task(CoughOverflowBase):
#     name: str
#     hello: str


# @app.post("/test")
# async def create_task(task: Task) -> Task:
#     redis: Redis = Redis.from_url(CONFIG.redis_url)
#     await redis.rpush("task_queue", task.model_dump_json())
#     return task


# @app.get("/test")
# async def get_task() -> Task:
#     redis = Redis.from_url(CONFIG.redis_url)
#     result: str | None = await redis.rpop("task_queue")
#     if result is None:
#         raise HTTPException(400, "No more in the queue")
#     return Task.model_validate_json(result)
