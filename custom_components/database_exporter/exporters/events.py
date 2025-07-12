"""Exporters for the database exporter component."""

import logging
from typing import override

from sqlalchemy import Insert, Select, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import selectinload

from homeassistant.components.recorder.db_schema import Events

from ..db_schema import ExportedEventData, ExportedEvents  # noqa: TID252
from .base import Exporter

_LOGGER = logging.getLogger(__name__)


class EventExporter(Exporter[Events], LOGGER=_LOGGER):
    """Exporter for events."""

    @override
    def _latest_exported_id_query(self) -> Select[tuple[int]]:
        event_id = ExportedEvents.event_id
        return select(event_id).order_by(event_id.desc()).limit(1)

    @override
    def _recorder_entries_query(
        self, start_id: float, limit: int
    ) -> Select[tuple[Events]]:
        return (
            select(Events)
            .options(selectinload(Events.event_data_rel))
            .options(selectinload(Events.event_type_rel))
            .filter(Events.event_id > start_id)
            .order_by(Events.event_id.asc())
            .limit(limit)
        )

    @override
    def _export_entries_queries(self, entries: list[Events]) -> list[Insert | None]:
        return [
            self._export_event_data_query(entries),
            self._export_events_query(entries),
        ]

    def _export_event_data_query(self, events: list[Events]) -> Insert | None:
        to_insert = [
            {"data_id": data_id, "value": model.to_native()}
            for data_id, model in {  # deduplicate data
                event.data_id: event.event_data_rel
                for event in events
                if event.data_id
                if event.event_data_rel
            }.items()
        ]

        if len(to_insert) == 0:
            return None

        stmt = sqlite_insert(ExportedEventData).values(to_insert)
        updates = {"value": stmt.excluded.value}
        return stmt.on_conflict_do_update(["data_id"], set_=updates)

    def _export_events_query(self, events: list[Events]) -> Insert | None:
        to_insert = [
            {
                "event_id": event.event_id,
                "origin_id": event.origin_idx,
                "time_fired_ts": event.time_fired_ts,
                "context_ulid": event.context_id_bin,
                "context_user_hex": event.context_user_id_bin,
                "context_parent_ulid": event.context_parent_id_bin,
                "event_type": event.event_type_rel.event_type,
                "data_id": event.data_id,
            }
            for event in events
        ]

        if len(to_insert) == 0:
            return None

        stmt = sqlite_insert(ExportedEvents).values(to_insert)
        cols = ExportedEvents.__table__.columns
        updates = {c.name: stmt.excluded[c.key] for c in cols if not c.primary_key}
        return stmt.on_conflict_do_update(["event_id"], set_=updates)
