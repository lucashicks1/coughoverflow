"""All models/schemas for health endpoints."""

from cough_overflow.models import CoughOverflowBase


class HealthItem(CoughOverflowBase):
    """Item/Service that is apart of health checks."""

    name: str
    healthy: bool
    reason: str | None = None


class HealthModel(CoughOverflowBase):
    """Schema for returning the health status."""

    health_items: list[HealthItem]
