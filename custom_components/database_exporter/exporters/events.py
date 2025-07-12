"""Exporters for the database exporter component."""

import logging
from typing import override

from sqlalchemy import Insert, Select, select
from sqlalchemy.orm import selectinload

from homeassistant.components.recorder.db_schema import Events

from ..db_schema import ExportedEventData, ExportedEvents
from ..upsert import upsert
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
            {
                ExportedEventData.data_id: data_id,
                ExportedEventData.value: model.to_native(),
            }
            for data_id, model in {  # deduplicate data
                event.data_id: event.event_data_rel
                for event in events
                if event.data_id
                if event.event_data_rel
            }.items()
        ]

        if len(to_insert) == 0:
            return None

        return (
            upsert(ExportedEventData)
            .values(to_insert)
            .on_conflict(ExportedEventData.data_id)
            .update(*ExportedEventData.__table__.columns)
        )

    def _export_events_query(self, events: list[Events]) -> Insert | None:
        to_insert = [
            {
                ExportedEvents.event_id: event.event_id,
                ExportedEvents.origin_id: event.origin_idx,
                ExportedEvents.time_fired_ts: event.time_fired_ts,
                ExportedEvents.context_ulid: event.context_id_bin,
                ExportedEvents.context_user_hex: event.context_user_id_bin,
                ExportedEvents.context_parent_ulid: event.context_parent_id_bin,
                ExportedEvents.event_type: event.event_type_rel.event_type,
                ExportedEvents.data_id: event.data_id,
            }
            for event in events
        ]

        if len(to_insert) == 0:
            return None

        return (
            upsert(ExportedEvents)
            .values(to_insert)
            .on_conflict(ExportedEvents.event_id)
            .update(*ExportedEvents.__table__.columns)
        )
