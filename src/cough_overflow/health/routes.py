"""Health Routes."""

from fastapi import APIRouter

from cough_overflow.health.models import HealthItem, HealthModel

r = router = APIRouter()


@r.get("")
async def get_health() -> HealthModel:
    """Query the health of the service."""
    return HealthModel(
        health_items=[
            HealthItem(name="Database", healthy=True),
        ],
    )
