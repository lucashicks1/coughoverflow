"""FastAPI Dependencies."""

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, Request

from cough_overflow.db import AsyncSession, get_session
from cough_overflow.jobs import TaskQueuer as TaskQueuerABC
from cough_overflow.jobs import get_queuer

if TYPE_CHECKING:
    from fastapi.dependencies.models import Dependant

DbSession = Annotated[AsyncSession, Depends(get_session)]

TaskQueuer = Annotated[TaskQueuerABC, Depends(get_queuer)]


# Credit: https://github.com/fastapi/fastapi/issues/2859
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
