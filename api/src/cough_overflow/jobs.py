"""Jobs Module."""

import asyncio
import base64
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

from loguru import logger

from cough_overflow.db import (
    AnalysisDBModel,
    get_session,
)
from cough_overflow.enums import AnalysisStatus
from cough_overflow.models import CoughOverflowBase

ENGINE_OUTPUT_MAP: dict[str, AnalysisStatus] = {
    "covid-19": AnalysisStatus.covid,
    "h5n1": AnalysisStatus.h5n1,
    "healthy": AnalysisStatus.healthy,
    "failed": AnalysisStatus.failed,
}


class AnalysisJob(CoughOverflowBase):
    """Analysis job to be added to task queue."""

    request_id: UUID
    encoded_image: str


class TaskQueuer(ABC):
    """ABC for task queueing."""

    @abstractmethod
    async def queue_task(self, job: AnalysisJob) -> None:
        """Abstract method for queueing a task.

        :param job: _description_
        :type job: AnalysisJob
        """


class InProcessTaskQueuer(TaskQueuer):
    """In process task queuer."""

    _tasks: set[asyncio.Task]

    def __init__(self) -> None:
        """Init."""
        self._tasks = set()

    async def queue_task(self, job: AnalysisJob) -> None:
        """Queues task."""
        self._tasks.add(asyncio.create_task(self.handle_task(job)))

    @staticmethod
    async def handle_task(job: AnalysisJob) -> None:
        """Handle analysis task."""
        async for session in get_session():
            analysis = await session.get(AnalysisDBModel, job.request_id)
            if analysis is None:
                msg = (
                    f"Unable to find analysis job under request id - '{job.request_id}'"
                )
                raise ValueError(msg)
            try:

                input_file_path = f"{job.request_id}-input.jpg"
                output_file_path = f"./{job.request_id}-output.txt"

                image_binary = base64.b64decode(job.encoded_image)

                # Write to input file
                with Path(input_file_path).open("wb") as f:
                    f.write(image_binary)

                # Call engine
                process = await asyncio.create_subprocess_exec(
                    "./overflowengine",
                    "--input",
                    input_file_path,
                    "--output",
                    output_file_path,
                )
                stdout, stderr = await process.communicate()

                logger.debug(f"Stdout is {stdout!r}")
                logger.debug(f"Stderr is {stderr!r}")

                status_code = process.returncode

                if status_code != 0:
                    msg = f"Encountered an issue when running overflowengine '{status_code}'"
                    logger.error(msg)
                    raise ValueError(msg)  # noqa: TRY301

                with Path(output_file_path).open("r") as f:
                    result = f.read().strip()

                analysis.result = ENGINE_OUTPUT_MAP.get(result, AnalysisStatus.failed)
                await session.commit()

            except Exception:
                analysis.result = AnalysisStatus.failed
                await session.commit()
                raise


def get_queuer() -> TaskQueuer:
    """Get Task Queuer."""
    return InProcessTaskQueuer()
