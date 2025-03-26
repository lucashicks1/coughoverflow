"""Errors module."""

from typing import Literal

from fastapi import HTTPException


class AnalysisHTTPException(HTTPException):
    """Custom HTTP Exception for POST endpoint of cough overflow API."""

    def __init__(
        self,
        error: Literal[
            "missing_patient_id",
            "invalid_patient_id",
            "missing_lab_id",
            "invalid_lab_id",
            "no_image",
            "invalid_image",
            "image_size",
            "unknown_error",
        ],
        detail: str | None = None,
    ) -> None:
        """Create custom exception for cough overflow."""
        info = {
            "error": error,
            "detail": detail,
        }
        super().__init__(400, info)
