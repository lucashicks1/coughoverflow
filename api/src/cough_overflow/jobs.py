"""Jobs Module."""

import asyncio
import base64
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from pathlib import Path
from uuid import UUID

from aiobotocore.session import AioSession
from aiobotocore.session import get_session as get_aio_session
from botocore.exceptions import ClientError as BotocoreClientError
from loguru import logger
from types_aiobotocore_sqs import SQSClient

from cough_overflow.config import CONFIG
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
    urgent: bool
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
                with Path(input_file_path).open("wb") as f:  # noqa: ASYNC230
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

                with Path(output_file_path).open("r") as f:  # noqa: ASYNC230
                    result = f.read().strip()

                analysis.result = ENGINE_OUTPUT_MAP.get(result, AnalysisStatus.failed)
                await session.commit()

            except Exception:
                analysis.result = AnalysisStatus.failed
                await session.commit()
                raise


class SQSTaskQueuer(TaskQueuer):
    """SQS Task Queuer."""

    _region: str
    _queue_url: str
    _urgent_queue_url: str

    _session: AioSession
    _client: SQSClient
    _exit_stack: AsyncExitStack

    def __init__(  # noqa: PLR0913
        self,
        region: str,
        queue_url: str,
        urgent_queue_url: str,
        session: AioSession,
        client: SQSClient,
        exit_stack: AsyncExitStack,
    ) -> None:
        """Create task queuer."""
        self._region = region

        self._queue_url = queue_url
        self._urgent_queue_url = urgent_queue_url

        self._session = session
        self._client = client
        self._exit_stack = exit_stack

    def set_url(self, queue_url: str) -> None:
        """Set queue url."""
        self._queue_url = queue_url

    @classmethod
    async def create(
        cls,
        region: str,
        main_queue_url: str,
        urgent_queue_url: str,
    ) -> "SQSTaskQueuer":
        """Create SQS Task Queuer."""
        session = get_aio_session()
        exit_stack = AsyncExitStack()

        client: SQSClient = await exit_stack.enter_async_context(
            session.create_client(
                service_name="sqs",
                region_name=region,
            ),
        )  # type:ignore[func-returns-value]

        return cls(
            region,
            main_queue_url,
            urgent_queue_url,
            session,
            client,
            exit_stack,
        )

    async def queue_task(self, job: AnalysisJob) -> None:
        """Queues task."""
        msg_body = job.model_dump_json()

        queue_url = self._urgent_queue_url if job.urgent else self._queue_url

        try:
            await self._client.send_message(
                QueueUrl=queue_url,
                MessageBody=msg_body,
            )
        except BotocoreClientError as e:
            logger.error(f"Encountered a botocore error: {e}")
            raise


class TaskQueuerProvider:
    """Task queuer provider."""

    _queuer: TaskQueuer | None = None

    @classmethod
    async def get_queuer(cls) -> TaskQueuer:
        """Get Task Queuer."""
        if cls._queuer is None:
            match CONFIG.queue_type:
                case "sqs":
                    cls._queuer = await SQSTaskQueuer.create(
                        CONFIG.aws_region,
                        CONFIG.aws_sqs_url,
                        CONFIG.aws_sqs_url_urgent,
                    )
                case "process":
                    cls._queuer = InProcessTaskQueuer()
        return cls._queuer
