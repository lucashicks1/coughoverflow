"""Base Models."""

from pydantic import BaseModel


class CoughOverflowBase(BaseModel):
    """Base Pydantic Model."""

    class Config:
        """Pydantic config."""
