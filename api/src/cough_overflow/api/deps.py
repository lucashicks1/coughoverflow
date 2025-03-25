"""FastAPI Dependencies."""

from typing import Annotated

from fastapi import Depends

from cough_overflow.db import AsyncSession, get_session
from cough_overflow.jobs import TaskQueuer as TaskQueuerABC
from cough_overflow.jobs import get_queuer

DbSession = Annotated[AsyncSession, Depends(get_session)]

TaskQueuer = Annotated[TaskQueuerABC, Depends(get_queuer)]
