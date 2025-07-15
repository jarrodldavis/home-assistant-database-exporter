"""Base Exporter for the database exporter component."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
import logging
from typing import Generic, TypeVar

from sqlalchemy import Insert, ReturnsRows, Select
from sqlalchemy.orm import Session

from homeassistant.components.recorder import get_instance as get_recorder_instance
from homeassistant.core import HomeAssistant

from ..types import ScopedSession

SourceModel = TypeVar("SourceModel")


class Exporter(ABC, Generic[SourceModel]):
    """Base class for an exporter."""

    _LOGGER = logging.getLogger(__name__)

    def __init_subclass__(cls, *, LOGGER: logging.Logger, **kwargs) -> None:
        """Initialize the subclass with a logger."""
        super().__init_subclass__(**kwargs)
        cls._LOGGER = LOGGER

    def __init__(self, export_session: ScopedSession, hass: HomeAssistant) -> None:
        """Initialize the exporter."""
        self.export_session = export_session
        self.hass = hass

    async def async_export_all(self) -> None:
        """Export all entries."""
        self._LOGGER.debug("Exporting all new batches")
        batch_count = 0
        while await self.async_export_batch():
            batch_count += 1
            self._LOGGER.debug("Exported batch %d successfully", batch_count)
        self._LOGGER.info("Exported %d batches successfully", batch_count)

    async def async_export_batch(self, limit: int = 1000) -> int:
        """Export the next batch of recorder entries."""
        hass_exec = self.hass.async_add_executor_job
        rec_exec = get_recorder_instance(self.hass).async_add_executor_job

        latest_exported_id = await hass_exec(self._get_latest_exported_id)
        start_id = latest_exported_id if latest_exported_id else 0
        self._LOGGER.debug("Exporting entries starting from ID %s", start_id)

        entries = await rec_exec(self._get_recorder_entries, start_id, limit)
        entry_count = len(entries)
        self._LOGGER.debug("Found %d new entries", entry_count)

        await hass_exec(self._export_entries, entries)
        self._LOGGER.info("Exported %d entries successfully", entry_count)

        return entry_count

    @abstractmethod
    def _latest_exported_id_query(self) -> Select[tuple[int]]:
        pass

    def _get_latest_exported_id(self) -> int | None:
        stmt = self._latest_exported_id_query()
        try:
            self._log_statement(stmt, self.export_session)
            return self.export_session.scalars(stmt).first()
        finally:
            self.export_session.remove()

    @abstractmethod
    def _recorder_entries_query(
        self, start_id: float, limit: int
    ) -> Select[tuple[SourceModel]]:
        pass

    def _get_recorder_entries(
        self, start_id: float, limit: int
    ) -> Sequence[SourceModel]:
        stmt = self._recorder_entries_query(start_id, limit)
        session = get_recorder_instance(self.hass).get_session()
        try:
            self._log_statement(stmt, session)
            results = session.scalars(stmt).all()
        finally:
            session.close()
        return results

    @abstractmethod
    def _export_entries_queries(
        self, entries: list[SourceModel]
    ) -> list[Insert | None]:
        pass

    def _export_entries(self, entries: list[SourceModel]) -> None:
        stmts = self._export_entries_queries(entries)
        stmts = [stmt for stmt in stmts if stmt is not None]
        try:
            for stmt in stmts:
                self._log_statement(stmt, self.export_session)
                self.export_session.execute(stmt)
            self.export_session.commit()
        finally:
            self.export_session.remove()

    def _log_statement(self, stmt: ReturnsRows, session: Session) -> None:
        if self._LOGGER.isEnabledFor(logging.DEBUG):
            compiled = stmt.compile(dialect=session.bind.dialect)
            self._LOGGER.debug("Executing statement: %s", compiled)
