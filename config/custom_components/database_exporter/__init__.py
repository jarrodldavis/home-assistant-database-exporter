"""The Database Exporter integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_DB_URL
from .core import DatabaseExportManager

_PLATFORMS: list[Platform] = []

type DatabaseExporterConfigEntry = ConfigEntry[DatabaseExportManager]


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
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        return False

    await entry.runtime_data.async_teardown()
    return True
