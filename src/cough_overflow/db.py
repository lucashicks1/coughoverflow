"""Database module."""

import datetime
from collections.abc import AsyncGenerator
from typing import Annotated, Any, ClassVar
from uuid import UUID

from fastapi import Depends
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column

from cough_overflow.config import CONFIG
from cough_overflow.models import AnalysisResult
from cough_overflow.enums import LabIdentifier, AnalysisStatus


class BaseDBModel(AsyncAttrs, DeclarativeBase, MappedAsDataclass):
    """Base model for dbs."""

    __mapper_args__: ClassVar[dict[str, Any]] = {"eager_defaults": True}  # type: ignore[reportIncompatibleVariableOverride]


class AnalysisDBModel(BaseDBModel):
    """Analysis db model."""

    __tablename__ = "analysis_job"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    lab_id: LabIdentifier
    patient_id: str
    result: AnalysisStatus
    urgent: bool
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.UTC),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
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


async def _get_session() -> AsyncGenerator[AsyncSession, None]:
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


DbSession = Annotated[AsyncSession, Depends(_get_session)]
