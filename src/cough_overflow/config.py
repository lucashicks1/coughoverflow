"""Config."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class GeneralSettings(BaseSettings):
    """General app settings."""

    db_url: str = Field()
    queue_url: str = Field()
    task_queue: Literal["redis"] = Field()


CONFIG = GeneralSettings()  # type: ignore[call-arg]
