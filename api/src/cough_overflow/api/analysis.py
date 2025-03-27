"""Analysis Routes."""

import base64
import binascii
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request

from cough_overflow.api.deps import DbSession, EmptyBodyCheck, TaskQueuer
from cough_overflow.db import AnalysisDBModel
from cough_overflow.enums import (
    LAB_IDENTIFIERS,
    MAX_IMAGE_SIZE,
    MEDICARE_NUM_LEN,
    MIN_IMAGE_SIZE,
    AnalysisStatus,
)
from cough_overflow.errors import AnalysisHTTPError
from cough_overflow.jobs import AnalysisJob
from cough_overflow.models import (
    AnalysisResult,
    InitialAnalysisResult,
)

r = router = APIRouter()


@r.get("")
async def get_analysis_result(
    db: DbSession,
    request: Request,
    _: EmptyBodyCheck,
) -> AnalysisResult:
    """Return the result or current status of the specified analysis request.

    :param request: The request object
    :type request: Request
    :return: The specified analysis request
    :rtype: AnalysisResult
    """
    params = dict(request.query_params)
    request_id: str | None = params.pop("request_id", None)
    if request_id is None:
        raise HTTPException(404, "request_id not given as a query parameter")

    if params != {}:
        raise HTTPException(400, f"Extras query params given - {list(params.keys())}")

    try:
        request_uuid: UUID = UUID(request_id)
    except ValueError as e:
        raise HTTPException(
            404,
            f"request_id is not a valid UUID - '{request_id}'",
        ) from e

    result = await db.get(AnalysisDBModel, request_uuid)
    if result is None:
        raise HTTPException(
            404,
            f"Analysis result cannot be found under id '{request_uuid}'",
        )
    return result.normalise()


@r.post("", status_code=201)
async def create_analysis(  # noqa: C901, PLR0912
    db: DbSession,
    task_queuer: TaskQueuer,
    request: Request,
) -> InitialAnalysisResult:
    """Request analysis of a sample."""
    # Validate the body
    try:
        body = await request.json()
    except Exception as e:
        raise AnalysisHTTPError(
            "unknown_error",
            "Request body is not valid JSON",
        ) from e

    if type(body) is not dict:
        raise AnalysisHTTPError(
            "unknown_error",
            "Request body is not an object",
        )

    # No image field was given
    image = body.pop("image", None)
    if image is None:
        raise AnalysisHTTPError(
            "no_image",
            "The 'image' field is missing in the request body",
        )

    # Request body has more than just 'image' field
    if body != {}:
        raise AnalysisHTTPError(
            "unknown_error",
            f"Request body has extra fields - {body}",
        )

    # Validate image
    try:
        raw_image = base64.b64decode(image)
    except binascii.Error as e:
        # Invalid image error
        raise AnalysisHTTPError(
            "invalid_image",
            f"Image is not valid base64 - {e}",
        ) from e

    # Validate image size
    image_size = len(raw_image)
    if image_size < MIN_IMAGE_SIZE or image_size > MAX_IMAGE_SIZE:
        raise AnalysisHTTPError(
            "image_size",
            f"Image is not a valid size - {image_size} bytes",
        )

    query_params = dict(request.query_params)

    # Check if patient_id is missing
    patient_id = query_params.pop("patient_id", None)
    if patient_id is None:
        raise AnalysisHTTPError(
            "missing_patient_id",
            "'patient_id' is missing in the query params",
        )

    # Validate structure of patient_id
    if len(patient_id) != MEDICARE_NUM_LEN or not patient_id.isnumeric():
        raise AnalysisHTTPError(
            "invalid_patient_id",
            f"'patient_id' is invalid - '{patient_id}'",
        )

    lab_id = query_params.pop("lab_id", None)
    if lab_id is None:
        raise AnalysisHTTPError(
            "missing_lab_id",
            "'lab_id' is missing in the query params",
        )

    if lab_id not in LAB_IDENTIFIERS:
        raise AnalysisHTTPError(
            "invalid_lab_id",
            "'lab_id' is not in the valid list of labs",
        )

    # Check whether urgent is valid
    urgent: bool
    urgent_param = query_params.pop("urgent", None)
    if urgent_param is None or urgent_param.lower() == "false":
        urgent = False
    elif urgent_param.lower() == "true":
        urgent = True
    else:
        raise AnalysisHTTPError(
            "unknown_error",
            f"'urgent' param is not a valid boolean - '{urgent_param}'",
        )

    # Check if extra query params
    if len(query_params) != 0:
        raise AnalysisHTTPError(
            "unknown_error",
            f"There are extra query params in request - {list(request.query_params.keys())}",
        )

    request_id = uuid4()

    # Create in the db
    analysis_entry = AnalysisDBModel(
        id=request_id,
        lab_id=lab_id,
        patient_id=patient_id,
        result=AnalysisStatus.pending,
        urgent=urgent,
    )
    db.add(analysis_entry)
    await db.commit()

    # Create the job
    job = AnalysisJob(request_id=request_id, encoded_image=image)
    await task_queuer.queue_task(job)

    return InitialAnalysisResult(
        id=request_id,
        created_at=analysis_entry.created_at,
        updated_at=analysis_entry.updated_at,
        status=analysis_entry.result,
    )


@r.put("")
async def update_analysis_job(
    db: DbSession,
    _: EmptyBodyCheck,
    request: Request,
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
    params = dict(request.query_params)

    request_id: str | None = params.pop("request_id", None)
    if request_id is None:
        raise HTTPException(404, "request_id not given as a query parameter")

    if params != {}:
        raise HTTPException(400, f"Extras query params given - {list(params.keys())}")

    try:
        request_uuid: UUID = UUID(request_id)
    except ValueError as e:
        raise HTTPException(
            404,
            f"request_id is not a valid UUID - '{request_id}'",
        ) from e

    if lab_id not in LAB_IDENTIFIERS:
        raise HTTPException(400, {"error": "invalid_lab_id"})

    result = await db.get(AnalysisDBModel, request_uuid)
    if result is None:
        raise HTTPException(
            404,
            f"Analysis result cannot be found under id '{request_uuid}'",
        )
    result.lab_id = lab_id
    await db.commit()
    return result.normalise()
