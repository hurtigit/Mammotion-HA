from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import MammotionConfigEntry
from .const import ATTR_DIRECTION
from .coordinator import MammotionDataUpdateCoordinator
from .entity import MammotionBaseEntity
from .error_handling import MammotionErrorHandling

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MammotionConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the RTK tracker from config entry."""
    coordinator: MammotionDataUpdateCoordinator = config_entry.runtime_data
    error_handler = MammotionErrorHandling(hass)

    try:
        async_add_entities([MammotionTracker(coordinator)])
    except Exception as error:
        error_handler.handle_error(error, "async_setup_entry")


class MammotionTracker(MammotionBaseEntity, TrackerEntity, RestoreEntity):
    """Mammotion device tracker."""

    _attr_force_update = False
    _attr_translation_key = "device_tracker"
    _attr_icon = "mdi:robot-mower"

    def __init__(self, coordinator: MammotionDataUpdateCoordinator) -> None:
        """Initialize the Tracker."""
        super().__init__(coordinator, f"{coordinator.device_name}_gps")
        self._attr_name = coordinator.device_name
        self.error_handler = MammotionErrorHandling(coordinator.hass)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        try:
            return {
                ATTR_DIRECTION: self.coordinator.manager.mower(
                    self.coordinator.device_name
                ).location.orientation
            }
        except Exception as error:
            self.error_handler.handle_error(error, "extra_state_attributes")
            return {}

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        try:
            return self.coordinator.manager.mower(
                self.coordinator.device_name
            ).location.device.latitude
        except Exception as error:
            self.error_handler.handle_error(error, "latitude")
            return None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        try:
            return self.coordinator.manager.mower(
                self.coordinator.device_name
            ).location.device.longitude
        except Exception as error:
            self.error_handler.handle_error(error, "longitude")
            return None

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the device."""
        try:
            return self.coordinator.data.report_data.dev.battery_val
        except Exception as error:
            self.error_handler.handle_error(error, "battery_level")
            return None

    @property
    def source_type(self) -> SourceType:
        """Return the source type, e.g., GPS or router, of the device."""
        return SourceType.GPS
