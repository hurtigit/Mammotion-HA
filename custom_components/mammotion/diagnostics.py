"""Diagnostics support for Mammotion."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import MammotionConfigEntry
from .error_handling import MammotionErrorHandling

TO_REDACT: list[str] = []


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: MammotionConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    error_handler = MammotionErrorHandling(hass)
    try:
        return async_redact_data(asdict(coordinator.data), TO_REDACT)
    except Exception as error:
        error_handler.handle_error(error, "async_get_config_entry_diagnostics")
        return {}
