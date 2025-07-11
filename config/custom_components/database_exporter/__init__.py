"""The Database Exporter integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import CONF_DB_URL, DOMAIN, SERVICE_EXPORT
from .core import DatabaseExportManager
from .services import async_setup_services

_PLATFORMS: list[Platform] = []

type DatabaseExporterConfigEntry = ConfigEntry[DatabaseExportManager]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up is called when Home Assistant is loading our component."""

    async_setup_services(hass)

    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: DatabaseExporterConfigEntry
) -> bool:
    """Set up Database Exporter from a config entry."""
    export_manager = DatabaseExportManager(hass, entry.data[CONF_DB_URL])
    await export_manager.async_setup()
    entry.runtime_data = export_manager
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: DatabaseExporterConfigEntry
) -> bool:
    """Teardown a Database Exporter config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        await entry.runtime_data.async_teardown()

        if not hass.config_entries.async_loaded_entries(DOMAIN):
            hass.services.async_remove(DOMAIN, SERVICE_EXPORT)

    return unload_ok
