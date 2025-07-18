"""Core module for the Home Assistant database export manager."""

from datetime import datetime
import logging
import sqlite3
from typing import Any

from cronsim import CronSim
import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import CALLBACK_TYPE, async_track_point_in_time
from homeassistant.util import dt as dt_util

from .db_schema import Base
from .exporters import EventExporter, Exporter, StateExporter
from .models import DatabaseExporterError, DatabaseExportManagerError
from .types import ScopedSession

_LOGGER = logging.getLogger(__name__)


class DatabaseExportManager:
    """The database export manager."""

    def __init__(self, hass: HomeAssistant, db_url: str) -> None:
        """Initialize the export manager."""
        self.hass = hass
        self.db_url = db_url
        self.session: ScopedSession | None = None
        self.exporters: list[Exporter] = []
        self.cron_event: CronSim | None = None
        self.remove_next_export_event: CALLBACK_TYPE | None = None
        self.next_export: datetime | None = None

    async def async_setup(self) -> None:
        """Set up the database export manager."""
        db_url = self.db_url

        if self.session:
            _LOGGER.debug("Resetting Database Export Manager with URL: %s", db_url)
            await self.async_teardown()

        _LOGGER.debug("Setting up Database Export Manager with URL: %s", db_url)
        self.session = await self.hass.async_add_executor_job(_init_session, db_url)
        self.exporters = [
            EventExporter(self.session, self.hass),
            StateExporter(self.session, self.hass),
        ]
        self._schedule_next()

    async def async_teardown(self) -> None:
        """Tear down the database export manager."""
        _LOGGER.debug("Tearing down Database Export Manager with URL: %s", self.db_url)
        self.exporters.clear()
        if self.session:
            await self.hass.async_add_executor_job(self.session.remove)
        self._unschedule_next()

    async def async_export_data(self) -> None:
        """Export data from the database."""
        if not self.session:
            raise DatabaseExportManagerError("Session is not initialized")

        _LOGGER.info("Exporting data to %s", self.db_url)
        try:
            for exporter in self.exporters:
                await exporter.async_export_all()
        except SQLAlchemyError as error:
            raise DatabaseExportManagerError("Export failed") from error
        _LOGGER.info("Finished exporting data to %s", self.db_url)

    @callback
    def _schedule_next(self) -> None:
        self._unschedule_next()

        if self.cron_event is None:
            self.cron_event = CronSim("23 * * * *", dt_util.now())

        async def _run_export(now: datetime) -> None:
            _LOGGER.debug("Running scheduled export at %s", now)
            self.remove_next_export_event = None
            self._schedule_next()

            try:
                await self.async_export_data()
            except DatabaseExporterError as error:
                _LOGGER.error("Error running export: %s", error)
            except Exception:
                _LOGGER.exception("Unexpected error running export")

        next_time = next(self.cron_event)
        _LOGGER.debug("Scheduling next export at %s", next_time)
        self.next_export = next_time
        event = async_track_point_in_time(self.hass, _run_export, next_time)
        self.remove_next_export_event = event

    @callback
    def _unschedule_next(self) -> None:
        """Unschedule the next export."""
        self.next_export = None
        if self.remove_next_export_event is not None:
            self.remove_next_export_event()
            self.remove_next_export_event = None


async def init_connection(hass: HomeAssistant, db_url: str) -> bool:
    """Test the database connection."""
    try:
        await hass.async_add_executor_job(_init_session, db_url)
    except SQLAlchemyError as error:
        raise DatabaseExportManagerError("Connection init failed") from error
    else:
        return True


def _init_session(db_url: str) -> ScopedSession:
    _LOGGER.debug("Initializing session for URL: %s", db_url)

    session: ScopedSession | None = None
    try:
        url = sqlalchemy.make_url(db_url)
        backend = url.get_backend_name()

        match backend:
            case "sqlite":
                _LOGGER.debug("Detected SQLite backend")
                engine = sqlalchemy.create_engine(url)
                sqlalchemy.event.listen(engine, "connect", _set_sqlite_pragmas)

            case _:
                _LOGGER.debug("Detected other backend: %s", backend)
                engine = sqlalchemy.create_engine(url)

        _LOGGER.debug("Creating tables")
        Base.metadata.create_all(engine)

        _LOGGER.debug("Creating session factory")
        session = scoped_session(sessionmaker(bind=engine, future=True))
        with session.begin():
            session.execute(sqlalchemy.text("SELECT 1;"))

        _LOGGER.debug("Session initialized successfully")
    except SQLAlchemyError as error:
        _LOGGER.exception("Couldn't initialize session")
        raise DatabaseExportManagerError("Session init failed") from error
    else:
        return session
    finally:
        session.remove() if session else None


def _set_sqlite_pragmas(conn: Any, _):
    _LOGGER.debug("Setting SQLite PRAGMAs")
    assert isinstance(conn, sqlite3.Connection)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = WAL")
    cur.execute("PRAGMA cache_size = -16384")
    cur.execute("PRAGMA synchronous = NORMAL")
    cur.execute("PRAGMA foreign_keys = ON")
    cur.close()
    _LOGGER.debug("Done setting SQLite PRAGMAs")


__all__ = [
    "DatabaseExportManager",
    "init_connection",
]
