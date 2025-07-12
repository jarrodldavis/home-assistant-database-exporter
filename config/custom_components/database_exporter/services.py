"""Services for the Database Exporter component."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    HomeAssistantError,
    ServiceCall,
    ServiceResponse,
    callback,
)

from .const import DOMAIN, SERVICE_EXPORT

if TYPE_CHECKING:
    from . import DatabaseExporterConfigEntry

_LOGGER = logging.getLogger(__name__)

SERVICE_EXPORT_SCHEMA = vol.Schema({})


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register services for Database Exporter integration."""

    async def handle_export(call: ServiceCall) -> ServiceResponse:
        _LOGGER.debug("Handling export service call")

        for entry in _get_entries(hass):
            _LOGGER.debug("Running export for entry: %s", entry.entry_id)

            try:
                await entry.runtime_data.async_export_data()
            except Exception as err:
                _LOGGER.exception("Error exporting data for entry %s:", entry.entry_id)
                raise HomeAssistantError("Failed to run export") from err

        return None

    hass.services.async_register(
        DOMAIN, SERVICE_EXPORT, handle_export, schema=SERVICE_EXPORT_SCHEMA
    )


def _get_entries(hass: HomeAssistant) -> list[DatabaseExporterConfigEntry]:
    return hass.config_entries.async_loaded_entries(DOMAIN)
