"""The Mammotion Luba integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_MAC, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_AEP_DATA,
    CONF_AUTH_DATA,
    CONF_DEVICE_DATA,
    CONF_REGION_DATA,
    CONF_RETRY_COUNT,
    CONF_SESSION_DATA,
    CONF_USE_WIFI,
    DEFAULT_RETRY_COUNT,
    DOMAIN,
)
from .coordinator import MammotionDataUpdateCoordinator
from .error_handling import MammotionErrorHandling

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.LAWN_MOWER,
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]

type MammotionConfigEntry = ConfigEntry[MammotionDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MammotionConfigEntry) -> bool:
    """Set up Mammotion Luba from a config entry."""
    assert entry.unique_id is not None

    error_handler = MammotionErrorHandling(hass)

    try:
        if CONF_ADDRESS not in entry.data and CONF_MAC in entry.data:
            # Bleak uses addresses not mac addresses which are actually
            # UUIDs on some platforms (MacOS).
            mac = entry.data[CONF_MAC]
            if "-" not in mac:
                mac = dr.format_mac(mac)
            hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, CONF_ADDRESS: mac},
            )

        if not entry.options:
            hass.config_entries.async_update_entry(
                entry,
                options={CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT},
            )

        mammotion_coordinator = MammotionDataUpdateCoordinator(hass, entry)
        await mammotion_coordinator.async_setup()

        # config_updates = {}
        mqtt = mammotion_coordinator.manager.mqtt_list.get(
            mammotion_coordinator.device_name
        )
        cloud_client = mqtt.cloud_client if mqtt else None

        if CONF_AUTH_DATA not in entry.data and cloud_client:
            config_updates = {
                **entry.data,
                CONF_AUTH_DATA: cloud_client.login_by_oauth_response,
                CONF_REGION_DATA: cloud_client.region_response,
                CONF_AEP_DATA: cloud_client.aep_response,
                CONF_SESSION_DATA: cloud_client.session_by_authcode_response,
                CONF_DEVICE_DATA: cloud_client.devices_by_account_response,
            }
            hass.config_entries.async_update_entry(entry, data=config_updates)

        await mammotion_coordinator.async_config_entry_first_refresh()
        entry.runtime_data = mammotion_coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # need to register service for triggering tasks
        # hass.services.async_register(DOMAIN, SERVICE_START_TASK, async_start_mowing)

        return True

    except Exception as error:
        error_handler.handle_error(error, "async_setup_entry")
        return False


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    error_handler = MammotionErrorHandling(hass)
    try:
        await hass.config_entries.async_reload(entry.entry_id)
    except Exception as error:
        error_handler.handle_error(error, "_async_update_listener")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    error_handler = MammotionErrorHandling(hass)
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if unload_ok:
            await hass.async_add_executor_job(
                entry.runtime_data.manager.remove_device, entry.runtime_data.device_name
            )
        return unload_ok
    except Exception as error:
        error_handler.handle_error(error, "async_unload_entry")
        return False
