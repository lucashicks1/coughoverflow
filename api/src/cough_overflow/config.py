"""Config."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class GeneralSettings(BaseSettings):
    """General app settings."""

    db_url: str = Field()
    queue_url: str = Field()
    queue_type: Literal["redis"] = Field()
    queue_name: str = Field(default="queue")


CONFIG = GeneralSettings()  # type: ignore[call-arg]
