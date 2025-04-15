"""Config."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class GeneralSettings(BaseSettings):
    """General app settings."""

    db_url: str = Field()
    queue_type: Literal["sqs", "process"] = Field(default="sqs")
    aws_region: str = Field(default="")
    aws_sqs_url: str = Field(default="")
    aws_sqs_url_urgent: str = Field(default="")


CONFIG = GeneralSettings()  # type: ignore[call-arg]
