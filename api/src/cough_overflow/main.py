"""Main App."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from cough_overflow import api
from cough_overflow.db import initialise_database


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    """App lifespan."""
    await initialise_database()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(api.router, prefix="/api/v1")
