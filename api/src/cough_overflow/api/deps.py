"""FastAPI Dependencies."""

import datetime
from typing import TYPE_CHECKING, Annotated

import pyrfc3339 as rfc3339
from fastapi import Depends, HTTPException, Request

from cough_overflow.db import AsyncSession, get_session
from cough_overflow.jobs import TaskQueuer as TaskQueuerABC
from cough_overflow.jobs import get_queuer

if TYPE_CHECKING:
    from fastapi.dependencies.models import Dependant

DbSession = Annotated[AsyncSession, Depends(get_session)]

TaskQueuer = Annotated[TaskQueuerABC, Depends(get_queuer)]


# Credit: https://github.com/fastapi/fastapi/issues/2859 [1]
def strict_query_params(request: Request) -> None:
    """Dependency to enforce no extra query params."""
    dependant: Dependant = request.scope["route"].dependant
    allowed_params = [
        param.alias
        for dependency in dependant.dependencies
        for param in dependency.query_params
    ]
    allowed_params += [modelfield.alias for modelfield in dependant.query_params]
    for requested_param, param_value in request.query_params.items():
        if requested_param not in allowed_params:
            raise HTTPException(
                400,
                f"Not allowed param: {requested_param}: {param_value}",
            )


QueryParamCheck = Annotated[None, Depends(strict_query_params)]


async def strict_no_request_body(request: Request) -> None:
    """Dependency to enforce no request body."""
    try:
        body = await request.body()
    except Exception as e:
        raise HTTPException(
            400,
            "No request body allowed",
        ) from e

    if body != b"":
        raise HTTPException(
            400,
            "No request body allowed",
        )


EmptyBodyCheck = Annotated[None, Depends(strict_no_request_body)]


def parse_rfc3339_datetime(dt_str: str) -> datetime.datetime:
    """Parse an RFC 3339 datetime string into a datetime object."""
    try:
        return rfc3339.parse(dt_str)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="Invalid RFC 3339 datetime format",
        ) from e


def parse_start_time(start: str | None = None) -> datetime.datetime | None:
    """Dependency to parse start time in endpoints."""
    if start is None:
        return None
    return parse_rfc3339_datetime(start)


def parse_end_time(end: str | None = None) -> datetime.datetime | None:
    """Dependency to parse end time in endpoints."""
    if end is None:
        return None
    return parse_rfc3339_datetime(end)


ParseStartDatetime = Annotated[datetime.datetime, Depends(parse_start_time)]
ParseEndDatetime = Annotated[datetime.datetime, Depends(parse_end_time)]
