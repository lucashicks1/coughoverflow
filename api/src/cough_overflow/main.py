"""Main App."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

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
async def validation_exception_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Intercept and transform validation errors."""
    logger.debug(f"Detail - '{exc.errors()}'")
    logger.debug(f"Body - '{exc.body}'")
    return JSONResponse(
        status_code=400,
        content=jsonable_encoder({"error": exc.errors(), "body": exc.body}),
    )
