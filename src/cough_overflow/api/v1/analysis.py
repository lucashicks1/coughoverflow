"""Analysis Routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from cough_overflow.db import AnalysisDBModel, DbSession
from cough_overflow.enums import LAB_IDENTIFIERS
from cough_overflow.models import (
    AnalysisResult,
    CreateAnalysisResult,
    InitialAnalysisResult,
)

r = router = APIRouter()


@r.get("")
async def get_analysis_result(db: DbSession, request_id: UUID) -> AnalysisResult:
    """Return the result or current status of the specified analysis request.

    :param request_id: The analysis request identifier.
    :type request_id: UUID
    :return: The specified analysis request
    :rtype: AnalysisResult
    """
    result = await db.get(AnalysisDBModel, request_id)
    if result is None:
        raise HTTPException(
            404,
            f"Analysis result cannot be found under id '{request_id}'",
        )
    return result.normalise()


@r.post("", status_code=201)
async def create_analysis(
    patient_id: Annotated[str, Query(regex=r"^\d{11}$")],
    lab_id: str,
    urgent: bool,
    body: CreateAnalysisResult,
) -> InitialAnalysisResult:
    """Request analysis of a sample.

    :param patient_id: Patient identifier - must be an eleven digit Medicare number (11 digits)
    :type patient_id: str
    :param lab_id: The lab identifier
    :type lab_id: str
    :param urgent: Flag to indicate whether this analysis has higher processing priority than a standard request.
    :type urgent: bool
    :param body: Request body containing image to be analysed
    :type body: CreateAnalysisResult
    :return: Message saying analysis job has been successfully created
    :rtype: InitialAnalysisResult
    """
    if lab_id not in LAB_IDENTIFIERS:
        raise HTTPException(400, {"error": "invalid_lab_id"})
    # TODO


@r.put("")
async def update_analysis_job(
    db: DbSession,
    request_id: UUID,
    lab_id: str,
) -> AnalysisResult:
    """Change the lab identifier for an analysis job to another lab's identifier.

    :param request_id: The identifier of the analysis job that is to be updated.
    :type request_id: UUID
    :param lab_id: The new lab identifier.
    :type lab_id: str
    :return: Message saying analysis job has been successfully updated with the new lab identifier.
    :rtype: AnalysisResult
    """
    if lab_id not in LAB_IDENTIFIERS:
        raise HTTPException(400, {"error": "invalid_lab_id"})

    result = await db.get(AnalysisDBModel, request_id)
    if result is None:
        raise HTTPException(
            404,
            f"Analysis result cannot be found under id '{request_id}'",
        )
    result.lab_id = lab_id
    await db.commit()
    return result.normalise()
