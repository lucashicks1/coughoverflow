"""Errors module."""

from typing import Literal


class AnalysisHTTPError(Exception):
    """Custom HTTP Exception for POST endpoint of cough overflow API."""

    detail: dict
    status_code: int

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
        info: str | None = None,
        status_code: int = 400,
    ) -> None:
        """Create custom exception for cough overflow."""
        self.detail = {
            "error": error,
            "detail": info,
        }
        self.status_code = status_code

    def __str__(self) -> str:  # noqa: D105
        return f"{self.status_code}: {self.detail}"

    def __repr__(self) -> str:  # noqa: D105
        class_name = self.__class__.__name__
        return f"{class_name}(status_code={self.status_code!r}, detail={self.detail!r})"
