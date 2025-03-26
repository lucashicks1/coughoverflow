"""Main App."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse

from cough_overflow import api
from cough_overflow.db import initialise_database


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    """App lifespan."""
    await initialise_database()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(api.router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=400)
