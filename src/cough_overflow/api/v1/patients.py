"""Patient routes."""

import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from cough_overflow.enums import AnalysisStatus
from cough_overflow.models import AnalysisResult

r = router = APIRouter()


@r.get("/results")
async def get_patient_jobs(
    patient_id: Annotated[str, Query(min_length=11, max_length=11)],
    start: datetime.date | None = None,
    end: datetime.date | None = None,
    status: AnalysisStatus | None = None,
    urgent: bool | None = False,  # noqa: FBT002
) -> list[AnalysisResult]:
    """List all analysis jobs associated with a patient.

    :param patient_id: Patient identifier - must be an eleven digit Medicare number (11 digits)
    :type patient_id: str
    :param start: Only return summary for analysis jobs submitted from this date.
        The date is in RFC3339 format, defaults to None
    :type start: datetime.date | None, optional
    :param end: Only return summary for analysis jobs submitted from before date.
        The date is in RFC3339 format, defaults to None
    :type end: datetime.date | None, optional
    :param status: Only return analysis jobs with this status, defaults to None
    :type status: AnalysisStatus | None, optional
    :param urgent: Only return analysis jobs that were flagged as being urgent, defaults to False
    :type urgent: bool | None, optional
    :return: list of the results of all analysis jobs associated with the provided patient identifier,
        with the optional filters applied.
    :rtype: list[AnalysisResult]
    """
