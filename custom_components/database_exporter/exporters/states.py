"""State Exporter for the database exporter component."""

import logging
from typing import override

from sqlalchemy import Insert, Select, select
from sqlalchemy.orm import selectinload

from homeassistant.components.recorder.db_schema import States

from ..db_schema import ExportedStateAttributes, ExportedStates
from ..upsert import upsert
from .base import Exporter

_LOGGER = logging.getLogger(__name__)


class StateExporter(Exporter[States], LOGGER=_LOGGER):
    """Exporter for states."""

    @override
    def _latest_exported_id_query(self) -> Select[tuple[int]]:
        state_id = ExportedStates.state_id
        return select(state_id).order_by(state_id.desc()).limit(1)

    @override
    def _recorder_entries_query(
        self, start_id: float, limit: int
    ) -> Select[tuple[States]]:
        return (
            select(States)
            .options(selectinload(States.states_meta_rel))
            .options(selectinload(States.state_attributes))
            .filter(States.state_id > start_id)
            .order_by(States.state_id.asc())
            .limit(limit)
        )

    @override
    def _export_entries_queries(self, entries: list[States]) -> list[Insert | None]:
        return [
            self._export_state_attributes_query(entries),
            self._export_states_query(entries),
        ]

    def _export_state_attributes_query(self, states: list[States]) -> Insert | None:
        to_insert = [
            {
                ExportedStateAttributes.attributes_id: attr_id,
                ExportedStateAttributes.value: model.to_native(),
            }
            for attr_id, model in {  # deduplicate attributes
                state.attributes_id: state.state_attributes
                for state in states
                if state.attributes_id
                if state.state_attributes
            }.items()
        ]

        if len(to_insert) == 0:
            return None

        return (
            upsert(ExportedStateAttributes)
            .values(to_insert)
            .on_conflict(ExportedStateAttributes.attributes_id)
            .update(*ExportedStateAttributes.__table__.columns)
        )

    def _export_states_query(self, states: list[States]) -> Insert | None:
        to_insert = [
            {
                ExportedStates.state_id: state.state_id,
                ExportedStates.state_value: state.state,
                ExportedStates.last_changed: state.last_changed_ts,
                ExportedStates.last_reported: state.last_reported_ts,
                ExportedStates.last_updated: state.last_updated_ts,
                ExportedStates.old_state_id: state.old_state_id,
                ExportedStates.origin_id: state.origin_idx,
                ExportedStates.context_ulid: state.context_id_bin,
                ExportedStates.context_user_hex: state.context_user_id_bin,
                ExportedStates.context_parent_ulid: state.context_parent_id_bin,
                ExportedStates.entity_id: state.states_meta_rel.entity_id,
                ExportedStates.attributes_id: state.attributes_id,
            }
            for state in states
        ]

        if len(to_insert) == 0:
            return None

        return (
            upsert(ExportedStates)
            .values(to_insert)
            .on_conflict(ExportedStates.state_id)
            .update(*ExportedStates.__table__.columns)
        )
