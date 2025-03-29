"""Base Models."""

import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel

from cough_overflow.enums import AnalysisStatus


def _serialize_datetime(v: datetime.datetime) -> str:
    return v.strftime("%Y-%m-%dT%H:%M:%SZ")


class CoughOverflowBase(BaseModel):
    """Base Pydantic Model."""

    class Config:
        """Pydantic config."""

        json_encoders: ClassVar = {
            datetime.datetime: _serialize_datetime,
        }


class AnalysisSummary(CoughOverflowBase):
    """Analysis Summary Model."""

    lab_id: str
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
    lab_id: str
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
    status: AnalysisStatus = AnalysisStatus.pending


class HealthItem(CoughOverflowBase):
    """Item/Service that is apart of health checks."""

    name: str
    healthy: bool
    reason: str | None = None


class HealthModel(CoughOverflowBase):
    """Schema for returning the health status."""

    health_items: list[HealthItem]
