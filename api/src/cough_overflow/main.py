"""Main App."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from loguru import logger

from cough_overflow import api
from cough_overflow.db import initialise_database
from cough_overflow.errors import AnalysisHTTPError


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    """App lifespan."""
    await initialise_database()
    yield


app = FastAPI(lifespan=lifespan, default_response_class=ORJSONResponse)
app.include_router(api.router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request,
    exc: RequestValidationError,
) -> ORJSONResponse:
    """Intercept and transform validation errors."""
    logger.debug(f"Detail - '{exc.errors()}'")
    logger.debug(f"Body - '{exc.body}'")
    return ORJSONResponse(
        status_code=400,
        content=jsonable_encoder({"error": exc.errors(), "body": exc.body}),
    )


@app.exception_handler(AnalysisHTTPError)
async def custom_http_exception_handler(
    _: Request,
    exc: AnalysisHTTPError,
) -> ORJSONResponse:
    """Handle the custom exceptions."""
    return ORJSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(exc.detail),
    )
