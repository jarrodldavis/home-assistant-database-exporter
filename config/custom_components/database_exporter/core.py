"""Core module for the Home Assistant database export manager."""

from datetime import datetime
import logging

from cronsim import CronSim
import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import CALLBACK_TYPE, async_track_point_in_time
from homeassistant.util import dt as dt_util

from .db_schema import Base
from .models import DatabaseExporterError, DatabaseExportManagerError

type Session = scoped_session

_LOGGER = logging.getLogger(__name__)


class DatabaseExportManager:
    """The database export manager."""

    def __init__(self, hass: HomeAssistant, db_url: str) -> None:
        """Initialize the export manager."""
        self.hass = hass
        self.db_url = db_url
        self.session: Session | None = None
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
        self._schedule_next()

    async def async_teardown(self) -> None:
        """Tear down the database export manager."""
        _LOGGER.debug("Tearing down Database Export Manager with URL: %s", self.db_url)
        if self.session:
            await self.hass.async_add_executor_job(self.session.remove)
        self._unschedule_next()

    async def async_export_data(self) -> None:
        """Export data from the database."""
        if not self.session:
            raise DatabaseExportManagerError("Session maker is not initialized")

        _LOGGER.info("Exporting data to %s", self.db_url)
        await self.hass.async_add_executor_job(_export_data, self.session)
        _LOGGER.info("Finished exporting data to %s", self.db_url)

    @callback
    def _schedule_next(self) -> None:
        self._unschedule_next()

        if self.cron_event is None:
            # At 3:12 AM every day
            self.cron_event = CronSim("12 3 * * *", dt_util.now())

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


def _init_session(db_url: str) -> Session:
    session: Session | None = None
    try:
        _LOGGER.debug("Creating session with DB_URL: %s", db_url)
        engine = sqlalchemy.create_engine(db_url)

        _LOGGER.debug("Creating tables for DB_URL: %s", db_url)
        Base.metadata.create_all(engine)

        _LOGGER.debug("Creating session for DB_URL: %s", db_url)
        session = scoped_session(sessionmaker(bind=engine, future=True))
        with session.begin():
            session.execute(sqlalchemy.text("SELECT 1;"))
    except SQLAlchemyError as error:
        _LOGGER.error("Couldn't connect using %s DB_URL: %s", db_url, error)
        raise DatabaseExportManagerError("Session init failed") from error
    else:
        return session
    finally:
        session.remove() if session else None


def _export_data(session: Session) -> None:
    try:
        with session.begin():
            # TODO: Perform the export logic here
            pass
    except SQLAlchemyError as error:
        raise DatabaseExportManagerError("Export failed") from error
    finally:
        session.remove()


__all__ = [
    "DatabaseExportManager",
    "init_connection",
]
