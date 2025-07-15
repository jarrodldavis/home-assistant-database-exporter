"""Database schema for the database exporter component."""

from sqlalchemy import (
    JSON,
    BigInteger,
    ForeignKey,
    Identity,
    Integer,
    LargeBinary,
    SmallInteger,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from homeassistant.const import (
    MAX_LENGTH_EVENT_EVENT_TYPE,
    MAX_LENGTH_STATE_ENTITY_ID,
    MAX_LENGTH_STATE_STATE,
)

TABLE_EXPORTED_EVENTS = "exported_events"
TABLE_EXPORTED_EVENTS_DATA = "exported_events_data"
TABLE_EXPORTED_STATES = "exported_states"
TABLE_EXPORTED_STATES_ATTRIBUTES = "exported_states_attributes"

ID_TYPE = BigInteger().with_variant(Integer(), "sqlite")


class Base(DeclarativeBase):
    """Base class for tables."""


class ExportedEventData(Base):
    """Table for exported events data."""

    __tablename__ = TABLE_EXPORTED_EVENTS_DATA

    id: Mapped[int] = mapped_column(ID_TYPE, Identity(), primary_key=True)

    # from `EventData` model
    data_id: Mapped[int] = mapped_column(ID_TYPE, index=True, unique=True)
    value: Mapped[dict] = mapped_column(JSON())


class ExportedEvents(Base):
    """Table for exported events."""

    __tablename__ = TABLE_EXPORTED_EVENTS

    id: Mapped[int] = mapped_column(ID_TYPE, Identity(), primary_key=True)

    # from `Events` model
    event_id: Mapped[int] = mapped_column(ID_TYPE, index=True, unique=True)
    origin_id: Mapped[int] = mapped_column(SmallInteger())
    time_fired_ts: Mapped[float] = mapped_column(index=True)
    context_ulid: Mapped[bytes | None] = mapped_column(LargeBinary(16))
    context_user_hex: Mapped[bytes | None] = mapped_column(LargeBinary(16))
    context_parent_ulid: Mapped[bytes | None] = mapped_column(LargeBinary(16))

    # from `EventTypes` model
    event_type: Mapped[str] = mapped_column(
        String(MAX_LENGTH_EVENT_EVENT_TYPE), index=True
    )

    # from `EventData` model
    data_id: Mapped[int | None] = mapped_column(
        ID_TYPE, ForeignKey(f"{TABLE_EXPORTED_EVENTS_DATA}.data_id")
    )
    data: Mapped[ExportedEventData | None] = relationship()


class ExportedStateAttributes(Base):
    """Table for exported states attributes."""

    __tablename__ = TABLE_EXPORTED_STATES_ATTRIBUTES

    id: Mapped[int] = mapped_column(ID_TYPE, Identity(), primary_key=True)

    # from `StateAttributes` model
    attributes_id: Mapped[int] = mapped_column(ID_TYPE, index=True, unique=True)
    value: Mapped[dict] = mapped_column(JSON())


class ExportedStates(Base):
    """Table for exported states."""

    __tablename__ = TABLE_EXPORTED_STATES

    id: Mapped[int] = mapped_column(ID_TYPE, Identity(), primary_key=True)

    # from `States` model
    state_id: Mapped[int] = mapped_column(ID_TYPE, index=True, unique=True)
    state_value: Mapped[str | None] = mapped_column(String(MAX_LENGTH_STATE_STATE))
    last_changed: Mapped[float | None]
    last_reported: Mapped[float | None]
    last_updated: Mapped[float] = mapped_column(index=True)
    old_state_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{TABLE_EXPORTED_STATES}.state_id"), use_alter=True
    )
    origin_id: Mapped[int] = mapped_column(SmallInteger())
    context_ulid: Mapped[bytes | None] = mapped_column(LargeBinary(16))
    context_user_hex: Mapped[bytes | None] = mapped_column(LargeBinary(16))
    context_parent_ulid: Mapped[bytes | None] = mapped_column(LargeBinary(16))

    # from `StatesMeta` model
    entity_id: Mapped[str] = mapped_column(
        String(MAX_LENGTH_STATE_ENTITY_ID), index=True
    )

    # from `StateAttributes` model
    attributes_id: Mapped[int | None] = mapped_column(
        ID_TYPE, ForeignKey(f"{TABLE_EXPORTED_STATES_ATTRIBUTES}.attributes_id")
    )
    attributes: Mapped[ExportedStateAttributes | None] = relationship()
