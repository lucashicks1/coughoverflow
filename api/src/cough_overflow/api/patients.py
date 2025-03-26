"""Patient routes."""

import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import Select
from sqlalchemy.sql import exists

from cough_overflow.api.deps import DbSession
from cough_overflow.db import AnalysisDBModel
from cough_overflow.enums import MEDICARE_NUM_LEN, AnalysisStatus
from cough_overflow.models import AnalysisResult

r = router = APIRouter()


@r.get("/results")
async def get_patient_jobs(  # noqa: PLR0913
    db: DbSession,
    patient_id: str,
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
    # Validate structure of patient_id
    if len(patient_id) != MEDICARE_NUM_LEN or not patient_id.isnumeric():
        raise HTTPException(
            404,
            f"patient_id needs to be an 11 character number - '{patient_id}'",
        )

    exists_stmt: Select = Select(
        exists().where(AnalysisDBModel.patient_id == patient_id),
    )

    patient_id_exists = await db.scalar(exists_stmt)

    if not patient_id_exists:
        raise HTTPException(
            404,
            f"patient_id can not be found - '{patient_id}'",
        )

    query: Select = Select(AnalysisDBModel).where(
        AnalysisDBModel.patient_id == patient_id,  # type: ignore[arg-type]
    )
    if start is not None:
        query = query.where(AnalysisDBModel.created_at > start)
    if end is not None:
        query = query.where(AnalysisDBModel.created_at < end)
    if status is not None:
        query = query.where(AnalysisDBModel.result == status)  # type: ignore[arg-type]
    if urgent:
        query = query.where(AnalysisDBModel.urgent is True)  # type: ignore[arg-type]

    results = await db.execute(query)

    return [result.normalise() for result in results]
