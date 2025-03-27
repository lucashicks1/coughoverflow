"""Database module."""

import datetime
from collections.abc import AsyncGenerator
from typing import Any, ClassVar
from uuid import UUID

from loguru import logger
from sqlalchemy import DateTime as SQLDatetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

from cough_overflow.config import CONFIG
from cough_overflow.enums import AnalysisStatus
from cough_overflow.models import AnalysisResult


class BaseDBModel(AsyncAttrs, DeclarativeBase):
    """Base model for dbs."""

    __mapper_args__: ClassVar[dict[str, Any]] = {"eager_defaults": True}  # type: ignore[misc]


class AnalysisDBModel(BaseDBModel):
    """Analysis db model."""

    __tablename__ = "analysis_job"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    lab_id: Mapped[str]
    patient_id: Mapped[str]
    result: Mapped[AnalysisStatus]
    urgent: Mapped[bool]
    updated_at: Mapped[datetime.datetime] = mapped_column(
        SQLDatetime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        SQLDatetime(timezone=True),
        server_default=func.now(),
    )

    def normalise(self) -> AnalysisResult:
        """Convert db model to object."""
        return AnalysisResult(
            request_id=self.id,
            lab_id=self.lab_id,
            patient_id=self.patient_id,
            result=self.result,
            urgent=self.urgent,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


engine: AsyncEngine = create_async_engine(
    CONFIG.db_url,
    pool_pre_ping=True,
)
session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def initialise_database() -> None:
    """Create tables if they don't exist already."""
    async with engine.begin() as conn:
        await conn.run_sync(BaseDBModel.metadata.create_all)

        logger.success("Initialising database was successful.")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get Database session."""
    async with session_factory() as session:
        try:
            yield session
            logger.info("Commit to the session")
            await session.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            await session.rollback()
            await session.close()
            raise
