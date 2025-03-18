"""Labs routes."""

import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from cough_overflow.enums import AnalysisStatus, LabIdentifier
from cough_overflow.models import AnalysisResult, AnalysisSummary

r = router = APIRouter()


@r.get("")
async def get_labs() -> list[LabIdentifier]:
    """List all labs with permission to use this service.

    :return: list of lab identifiers for all labs that are allowed to use this service.
    :rtype: list[LabIdentifier]
    """
    return list(LabIdentifier.__args__)


@r.get("/results/{lab_id}")
async def get_lab_jobs(  # noqa: PLR0913
    lab_id: LabIdentifier,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
    patient_id: Annotated[str | None, Query(min_length=11, max_length=11)] = None,
    status: AnalysisStatus | None = None,
    urgent: bool | None = False,
) -> list[AnalysisResult]:
    """List all analysis jobs associated with a lab.

    :param lab_id: The lab identifier
    :type lab_id: LabIdentifier
    :param limit: Returns up to a maximum of the specified number of results, defaults to 100, 0 < limit <= 1000
    :type limit: Annotated[int, Query, optional
    :param offset: _description_, defaults to 0, 0 <= offset
    :type offset: int, optional
    :param start: Only return summary for analysis jobs submitted from this date.
        The date is in RFC3339 format, defaults to None
    :type start: datetime.date | None, optional
    :param end: Only return summary for analysis jobs submitted from before date.
        The date is in RFC3339 format, defaults to None
    :type end: datetime.date | None, optional
    :param patient_id: Only return analysis jobs for this patient identifier.
        The patient id must be an eleven digit Medicare number (11 digits)
    :type patient_id: Annotated[str  |  None, Query, optional
    :param status: Only return analysis jobs with this status, defaults to None
    :type status: AnalysisStatus | None, optional
    :param urgent: Only return analysis jobs that were flagged as being urgent, defaults to False
    :type urgent: bool | None, optional
    :return: _description_
    :rtype: list[AnalysisResult]
    """


@r.get("/results/{lab_id}/summary")
async def get_lab_jobs_summary(
    lab_id: LabIdentifier,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
) -> AnalysisSummary:
    """Summary of analysis jobs associated with this lab.

    :param lab_id: The lab identifier
    :type lab_id: LabIdentifier
    :param start: Only return summary for analysis jobs submitted from this date.
        The date is in RFC3339 format, defaults to None
    :type start: datetime.date | None, optional
    :param end: Only return summary for analysis jobs submitted from before date.
        The date is in RFC3339 format, defaults to None
    :type end: datetime.date | None, optional
    :return: Summary of the number of analysis jobs submitted
    :rtype: AnalysisSummary
    """
