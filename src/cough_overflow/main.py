"""Main App."""

from fastapi import APIRouter, FastAPI

from cough_overflow.health.routes import router as health_router

base = APIRouter(prefix="/api/v1")
base.include_router(health_router, prefix="/health")


# Include other routers here


app = FastAPI()
app.include_router(base)
