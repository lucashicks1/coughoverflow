"""Analysis Routes."""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query

from cough_overflow.api.deps import DbSession, TaskQueuer
from cough_overflow.db import AnalysisDBModel
from cough_overflow.enums import LAB_IDENTIFIERS, AnalysisStatus
from cough_overflow.jobs import AnalysisJob
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
async def create_analysis(  # noqa: PLR0913
    db: DbSession,
    task_queuer: TaskQueuer,
    body: CreateAnalysisResult,
    patient_id: Annotated[str, Query(regex=r"^\d{11}$")],
    lab_id: str,
    urgent: bool | None = None,
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
    request_id = uuid4()

    job = AnalysisJob(request_id=request_id, raw_image=body.get_raw_image)
    await task_queuer.queue_task(job)

    # Create in the db
    analysis_entry = AnalysisDBModel(
        id=request_id,
        lab_id=lab_id,
        patient_id=patient_id,
        result=AnalysisStatus.pending,
        urgent=urgent is not None,
    )
    db.add(analysis_entry)
    await db.commit()
    return InitialAnalysisResult(
        id=request_id,
        created_at=analysis_entry.created_at,
        updated_at=analysis_entry.updated_at,
        status=analysis_entry.result,
    )


@r.get("/test-queue")
async def test_task_queue(
    task_queuer: TaskQueuer,
) -> AnalysisJob | None:
    return await task_queuer.dequeue_task()


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
