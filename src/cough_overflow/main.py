"""Main App."""

from fastapi import FastAPI

from cough_overflow.api import v1

app = FastAPI()
app.include_router(v1.router, prefix="/api/v1")
