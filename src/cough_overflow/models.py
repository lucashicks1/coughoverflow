"""Base Models."""

import base64
import binascii
import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator
from pydantic_core import PydanticCustomError

from cough_overflow.enums import AnalysisStatus, LabIdentifier


class CoughOverflowBase(BaseModel):
    """Base Pydantic Model."""

    class Config:
        """Pydantic config."""


class AnalysisSummary(CoughOverflowBase):
    """Analysis Summary Model."""

    lab_id: LabIdentifier
    pending: int
    covid: int
    h5n1: int
    healthy: int
    failed: int
    urgent: int
    generated_at: datetime.datetime


class AnalysisResult(CoughOverflowBase):
    """Analysis result Model."""

    request_id: UUID
    lab_id: LabIdentifier
    patient_id: str
    result: AnalysisStatus
    urgent: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime


class InitialAnalysisResult(CoughOverflowBase):
    """Model for when analysis job has been successfully created."""

    id: UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    status: AnalysisStatus = AnalysisStatus.PENDING


NUM_B_IN_KB = 1024
MIN_IMAGE_SIZE = 4 * NUM_B_IN_KB
MAX_IMAGE_SIZE = 150 * NUM_B_IN_KB


class CreateAnalysisResult(CoughOverflowBase):
    """Create analysis request."""

    image: str

    @field_validator("image", mode="after")
    @classmethod
    def validate_image(cls, value: str) -> str:
        """Validate whether the image field is base64 and is the correct size."""
        try:
            decoded_bytes = base64.b64decode(value)
        except binascii.Error as e:
            error_type = "invalid"
            msg = "Invalid base64 encoding"
            raise PydanticCustomError(
                error_type,
                msg,
                {"context": f"The following value is not valid base64 - '{value}'"},
            ) from e
        size = len(decoded_bytes)
        if size < MIN_IMAGE_SIZE or size > MAX_IMAGE_SIZE:
            msg = f"Image size must be between {MIN_IMAGE_SIZE}B and {MAX_IMAGE_SIZE}B"
            error_type = "size"
            raise PydanticCustomError(
                error_type,
                msg,
                {"context": msg},
            )

        return value


class HealthItem(CoughOverflowBase):
    """Item/Service that is apart of health checks."""

    name: str
    healthy: bool
    reason: str | None = None


class HealthModel(CoughOverflowBase):
    """Schema for returning the health status."""

    health_items: list[HealthItem]
