"""Luba lawn mowers."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pymammotion.data.model.device_config import OperationSettings
from pymammotion.data.model.report_info import ReportData
from pymammotion.proto import has_field
from pymammotion.proto.luba_msg import RptDevStatus
from pymammotion.utility.constant.device_constant import WorkMode

from . import MammotionConfigEntry
from .const import COMMAND_EXCEPTIONS, DOMAIN, LOGGER
from .coordinator import MammotionDataUpdateCoordinator
from .entity import MammotionBaseEntity
from .error_handling import MammotionErrorHandling

SERVICE_START_MOWING = "start_mow"

START_MOW_SCHEMA = {
    vol.Optional("is_mow", default=True): cv.boolean,
    vol.Optional("is_dump", default=True): cv.boolean,
    vol.Optional("is_edge", default=False): cv.boolean,
    vol.Optional("collect_grass_frequency", default=10): vol.All(
        vol.Coerce(int), vol.Range(min=5, max=100)
    ),
    vol.Optional("job_mode", default=0): vol.Coerce(int),
    vol.Optional("job_version", default=0): vol.Coerce(int),
    vol.Optional("job_id", default=0): vol.Coerce(int),
    vol.Optional("speed", default=0.3): vol.All(
        vol.Coerce(float), vol.Range(min=0.2, max=1.2)
    ),
    vol.Optional("ultra_wave", default=2): vol.In([0, 1, 2, 10]),
    vol.Optional("channel_mode", default=0): vol.In([0, 1, 2, 3]),
    vol.Optional("channel_width", default=25): vol.All(
        vol.Coerce(int), vol.Range(min=20, max=35)
    ),
    vol.Optional("rain_tactics", default=1): vol.In([0, 1]),
    vol.Optional("blade_height", default=25): vol.All(
        vol.Coerce(int), vol.Range(min=15, max=100)
    ),
    vol.Optional("path_order", default=0): vol.In([0, 1]),
    vol.Optional("toward", default=0): vol.All(
        vol.Coerce(int), vol.Range(min=-180, max=180)
    ),
    vol.Optional("toward_included_angle", default=0): vol.All(
        vol.Coerce(int), vol.Range(min=-180, max=180)
    ),
    vol.Optional("toward_mode", default=0): vol.In([0, 1, 2]),
    vol.Optional("border_mode", default=1): vol.In([0, 1, 2, 3, 4]),
    vol.Optional("obstacle_laps", default=1): vol.In([0, 1, 2, 3, 4]),
    vol.Optional("start_progress", default=0): vol.All(
        vol.Coerce(int), vol.Range(min=0, max=100)
    ),
    vol.Required("areas"): vol.All(
        cv.ensure_list, [cv.entity_id]
    ),  # This assumes `areas` are entity IDs from the integration
}


def get_entity_attribute(hass, entity_id, attribute_name):
    # Get the state object of the entity
    entity = hass.states.get(entity_id)

    # Check if the entity exists and has attributes
    if entity and attribute_name in entity.attributes:
        # Return the specific attribute
        return entity.attributes[attribute_name]
    else:
        # Return None if the entity or attribute does not exist
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MammotionConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Luba config entry."""
    coordinator = entry.runtime_data
    async_add_entities([MammotionLawnMowerEntity(coordinator)])

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_START_MOWING, START_MOW_SCHEMA, "async_start_mowing"
    )


class MammotionLawnMowerEntity(MammotionBaseEntity, LawnMowerEntity):
    """Representation of a Mammotion lawn mower."""

    _attr_supported_features = (
        LawnMowerEntityFeature.DOCK
        | LawnMowerEntityFeature.PAUSE
        | LawnMowerEntityFeature.START_MOWING
    )

    def __init__(self, coordinator: MammotionDataUpdateCoordinator) -> None:
        """Initialize the lawn mower."""
        super().__init__(coordinator, "mower")
        self._attr_name = None  # main feature of device
        self.error_handler = MammotionErrorHandling(coordinator.hass)

    @property
    def rpt_dev_status(self) -> RptDevStatus | None:
        """Return the device status."""
        if has_field(self.coordinator.data.sys.toapp_report_data.dev):
            return self.coordinator.data.sys.toapp_report_data.dev
        return None

    @property
    def report_data(self) -> ReportData:
        return self.coordinator.data.report_data

    @property
    def activity(self) -> LawnMowerActivity | None:
        """Return the state of the mower."""

        if self.rpt_dev_status is None:
            return None

        mode = self.rpt_dev_status.sys_status
        charge_state = self.rpt_dev_status.charge_state

        LOGGER.debug("activity mode %s", mode)
        if (
            mode == WorkMode.MODE_PAUSE
            or mode == WorkMode.MODE_READY
            and charge_state == 0
        ):
            return LawnMowerActivity.PAUSED
        if mode in (WorkMode.MODE_WORKING, WorkMode.MODE_RETURNING):
            return LawnMowerActivity.MOWING
        if mode == WorkMode.MODE_LOCK:
            return LawnMowerActivity.ERROR
        if mode == WorkMode.MODE_READY and charge_state != 0:
            return LawnMowerActivity.DOCKED
        return None

    async def async_start_mowing(self, **kwargs: Any) -> None:
        """Start mowing."""
        try:
            if kwargs:
                entity_ids = kwargs.get("areas", [])

                attributes = [
                    get_entity_attribute(self.hass, entity_id, "hash")
                    for entity_id in entity_ids
                    if get_entity_attribute(self.hass, entity_id, "hash") is not None
                ]
                kwargs["areas"] = attributes
                operational_settings = OperationSettings.from_dict(kwargs)
                LOGGER.debug(kwargs)
                await self.coordinator.async_plan_route(operational_settings)
                await self.coordinator.async_send_command("start_job")
                await self.coordinator.async_request_iot_sync()
                return

            # check if job in progress
            #
            if self.rpt_dev_status is None:
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="device_not_ready"
                )
            work_area = self.report_data.work.area >> 16

            if work_area > 0 and self.rpt_dev_status.sys_status in (
                WorkMode.MODE_PAUSE,
                WorkMode.MODE_READY,
            ):
                try:
                    await self.coordinator.async_send_command("resume_execute_task")
                    return await self.coordinator.async_request_iot_sync()
                except COMMAND_EXCEPTIONS as exc:
                    raise HomeAssistantError(
                        translation_domain=DOMAIN, translation_key="resume_failed"
                    ) from exc
            try:
                await self.coordinator.async_plan_route(self.coordinator.operation_settings)
                await self.coordinator.async_send_command("start_job")
                await self.coordinator.async_request_iot_sync()
            except COMMAND_EXCEPTIONS as exc:
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="start_failed"
                ) from exc
        except Exception as error:
            self.error_handler.handle_error(error, "async_start_mowing")

    async def async_dock(self) -> None:
        """Start docking."""
        try:
            mode = self.rpt_dev_status.sys_status
            if mode is None:
                mode = WorkMode.MODE_READY

            try:
                if mode == WorkMode.MODE_RETURNING:
                    await self.coordinator.async_send_command("cancel_return_to_dock")
                    return await self.coordinator.async_request_iot_sync()
                if mode == WorkMode.MODE_WORKING:
                    await self.coordinator.async_send_command("pause_execute_task")
                await self.coordinator.async_send_command("return_to_dock")
                await self.coordinator.async_request_iot_sync()
            except COMMAND_EXCEPTIONS as exc:
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="dock_failed"
                ) from exc
            finally:
                self.coordinator.async_set_updated_data(
                    self.coordinator.manager.mower(self.coordinator.device_name)
                )
            return
        except Exception as error:
            self.error_handler.handle_error(error, "async_dock")

    async def async_pause(self) -> None:
        """Pause mower."""
        try:
            await self.coordinator.async_send_command("pause_execute_task")
            await self.coordinator.async_request_iot_sync()
        except COMMAND_EXCEPTIONS as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="pause_failed"
            ) from exc
        finally:
            self.coordinator.async_set_updated_data(
                self.coordinator.manager.mower(self.coordinator.device_name)
            )
        except Exception as error:
            self.error_handler.handle_error(error, "async_pause")
