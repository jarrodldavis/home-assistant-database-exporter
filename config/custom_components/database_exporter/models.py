"""Models for the database exporter integration."""

from homeassistant.exceptions import HomeAssistantError


class DatabaseExporterError(HomeAssistantError):
    """Base class for database exporter errors."""

    error_code = "unknown"


class DatabaseExportManagerError(DatabaseExporterError):
    """Database export manager error."""

    error_code = "database_export_manager_error"
