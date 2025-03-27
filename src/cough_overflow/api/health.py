"""Health Routes."""

from fastapi import APIRouter

from cough_overflow.api.deps import EmptyBodyCheck, QueryParamCheck
from cough_overflow.models import HealthItem, HealthModel

r = router = APIRouter()


@r.get("")
async def get_health(
    _: QueryParamCheck,
    __: EmptyBodyCheck,
) -> HealthModel:
    """Query the health of the service."""
    return HealthModel(
        health_items=[
            HealthItem(name="Database", healthy=True),
        ],
    )
