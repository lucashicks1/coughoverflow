"""Health Routes."""

from fastapi import APIRouter, Depends

from cough_overflow.api.deps import strict_query_params
from cough_overflow.models import HealthItem, HealthModel

r = router = APIRouter()


@r.get("")
async def get_health(_=Depends(strict_query_params)) -> HealthModel:  # noqa: ANN001
    """Query the health of the service."""
    return HealthModel(
        health_items=[
            HealthItem(name="Database", healthy=True),
        ],
    )
