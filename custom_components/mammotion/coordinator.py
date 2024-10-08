"""Provides the mammotion DataUpdateCoordinator."""

from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import betterproto
from aiohttp import ClientConnectorError
from homeassistant.components import bluetooth
from homeassistant.const import CONF_ADDRESS, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymammotion.aliyun.cloud_gateway import DeviceOfflineException, SetupException
from pymammotion.data.model import GenerateRouteInformation, HashList
from pymammotion.data.model.account import Credentials
from pymammotion.data.model.device import MowingDevice
from pymammotion.data.model.device_config import OperationSettings, create_path_order
from pymammotion.mammotion.devices.mammotion import (
    ConnectionPreference,
    Mammotion,
)
from pymammotion.proto import has_field
from pymammotion.proto.luba_msg import LubaMsg
from pymammotion.proto.mctrl_sys import RptAct, RptInfoType

from .const import (
    COMMAND_EXCEPTIONS,
    CONF_ACCOUNTNAME,
    CONF_DEVICE_NAME,
    CONF_STAY_CONNECTED_BLUETOOTH,
    CONF_USE_WIFI,
    DOMAIN,
    LOGGER,
)
from .error_handling import MammotionErrorHandling

if TYPE_CHECKING:
    from . import MammotionConfigEntry

UPDATE_INTERVAL = timedelta(minutes=1)


class MammotionDataUpdateCoordinator(DataUpdateCoordinator[MowingDevice]):
    """Class to manage fetching mammotion data."""

    address: str | None = None
    config_entry: MammotionConfigEntry
    manager: Mammotion = None
    _operation_settings: OperationSettings

    def __init__(self, hass: HomeAssistant, config_entry: MammotionConfigEntry) -> None:
        """Initialize global mammotion data updater."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        assert self.config_entry.unique_id
        self.config_entry = config_entry
        self._operation_settings = OperationSettings()
        self.update_failures = 0
        self.error_handler = MammotionErrorHandling(hass)

    async def async_setup(self) -> None:
        """Set coordinator up."""
        ble_device = None
        credentials = None
        preference = (
            ConnectionPreference.WIFI
            if self.config_entry.data.get(CONF_USE_WIFI, False)
            else ConnectionPreference.BLUETOOTH
        )
        address = self.config_entry.data.get(CONF_ADDRESS)
        name = self.config_entry.data.get(CONF_DEVICE_NAME)
        account = self.config_entry.data.get(CONF_ACCOUNTNAME)
        password = self.config_entry.data.get(CONF_PASSWORD)
        stay_connected_ble = self.config_entry.options.get(
            CONF_STAY_CONNECTED_BLUETOOTH, False
        )

        if name:
            self.device_name = name

        if self.manager is None or self.manager.get_device_by_name(name) is None:
            self.manager = Mammotion()
            if account and password:
                credentials = Credentials()
                credentials.email = account
                credentials.password = password
                try:
                    await self.manager.login_and_initiate_cloud(account, password)
                except ClientConnectorError as err:
                    self.error_handler.handle_error(err, "async_setup")
                    raise ConfigEntryNotReady(err)
                except Exception as e:
                    LOGGER.error(f"Error during login_and_initiate_cloud: {e}")
                    self.error_handler.handle_error(e, "async_setup")
                    raise ConfigEntryNotReady from e

                # address previous bugs
                if address is None and preference == ConnectionPreference.BLUETOOTH:
                    preference = ConnectionPreference.WIFI

            if address:
                ble_device = bluetooth.async_ble_device_from_address(self.hass, address)
                if not ble_device and credentials is None:
                    self.error_handler.handle_error(
                        Exception(f"Could not find Mammotion lawn mower with address {address}"),
                        "async_setup",
                    )
                    raise ConfigEntryNotReady(
                        f"Could not find Mammotion lawn mower with address {address}"
                    )
                if ble_device is not None:
                    self.device_name = ble_device.name or "Unknown"
                    self.address = address
                    self.manager.add_ble_device(ble_device, preference)

        device = self.manager.get_device_by_name(self.device_name)
        device.preference = preference

        if ble_device and device:
            device.ble().set_disconnect_strategy(not stay_connected_ble)

        cloud_client = device.cloud().mqtt.cloud_client if device.cloud() else None

        if device is None and cloud_client:
            device_list = cloud_client.devices_by_account_response.data.data
            mowing_devices = [
                dev
                for dev in device_list
                if (dev.productModel is None or dev.productModel != "ReferenceStation")
            ]
            if len(mowing_devices) > 0:
                self.device_name = mowing_devices[0].deviceName
                device = self.manager.get_device_by_name(self.device_name)
            else:
                self.error_handler.handle_error(
                    Exception(f"Could not find Mammotion lawn mower with name {self.device_name}"),
                    "async_setup",
                )
                raise ConfigEntryNotReady(
                    f"Could not find Mammotion lawn mower with name {self.device_name}"
                )

        try:
            if preference is ConnectionPreference.WIFI and device.cloud():
                await device.cloud().start_sync(0)
                device.cloud().set_notification_callback(
                    self._async_update_notification
                )
            elif device.ble():
                await device.ble().start_sync(0)
                device.ble().set_notification_callback(self._async_update_notification)
            else:
                self.error_handler.handle_error(
                    Exception("No configuration available to setup Mammotion lawn mower"),
                    "async_setup",
                )
                raise ConfigEntryNotReady(
                    "No configuration available to setup Mammotion lawn mower"
                )

        except COMMAND_EXCEPTIONS as exc:
            self.error_handler.handle_error(exc, "async_setup")
            raise ConfigEntryNotReady("Unable to setup Mammotion device") from exc

        await self.async_restore_data()

    async def async_restore_data(self) -> None:
        """Restore saved data."""
        store = Store(self.hass, version=1, key=self.device_name)
        try:
            restored_data = await store.async_load()
            if restored_data:
                if device_dict := restored_data.get("device"):
                    restored_data["device"] = None
                else:
                    device_dict = LubaMsg().to_dict(casing=betterproto.Casing.SNAKE)

                self.data = MowingDevice().from_dict(restored_data)
                self.data.update_raw(device_dict)
                self.manager.get_device_by_name(self.device_name).mower_state = self.data
        except Exception as error:
            self.error_handler.handle_error(error, "async_restore_data")

    async def async_save_data(self, data: MowingDevice) -> None:
        """Get map data from the device."""
        store = Store(self.hass, version=1, key=self.device_name)
        try:
            stored_data = asdict(data)
            await store.async_save(stored_data)
        except Exception as error:
            self.error_handler.handle_error(error, "async_save_data")

    async def async_sync_maps(self) -> None:
        """Get map data from the device."""
        try:
            await self.manager.start_map_sync(self.device_name)
        except Exception as error:
            self.error_handler.handle_error(error, "async_sync_maps")

    async def async_start_stop_blades(self, start_stop: bool) -> None:
        try:
            if start_stop:
                await self.async_send_command("set_blade_control", on_off=1)
            else:
                await self.async_send_command("set_blade_control", on_off=0)
        except Exception as error:
            self.error_handler.handle_error(error, "async_start_stop_blades")

    async def async_set_sidelight(self, on_off: int) -> None:
        """Set Sidelight."""
        try:
            await self.async_send_command(
                "read_and_set_sidelight", is_sidelight=bool(on_off), operate=0
            )
        except Exception as error:
            self.error_handler.handle_error(error, "async_set_sidelight")

    async def async_read_sidelight(self) -> None:
        """Set Sidelight."""
        try:
            await self.async_send_command(
                "read_and_set_sidelight", is_sidelight=False, operate=1
            )
        except Exception as error:
            self.error_handler.handle_error(error, "async_read_sidelight")

    async def async_blade_height(self, height: int) -> int:
        """Set blade height."""
        try:
            await self.async_send_command("set_blade_height", height=float(height))
            return height
        except Exception as error:
            self.error_handler.handle_error(error, "async_blade_height")
            return 0

    async def async_leave_dock(self) -> None:
        """Leave dock."""
        try:
            await self.async_send_command("leave_dock")
        except Exception as error:
            self.error_handler.handle_error(error, "async_leave_dock")

    async def async_cancel_task(self) -> None:
        """Cancel task."""
        try:
            await self.async_send_command("cancel_job")
        except Exception as error:
            self.error_handler.handle_error(error, "async_cancel_task")

    async def async_move_forward(self, speed: float) -> None:
        """Move forward."""
        try:
            await self.async_send_command("move_forward", linear=speed)
        except Exception as error:
            self.error_handler.handle_error(error, "async_move_forward")

    async def async_move_left(self, speed: float) -> None:
        """Move left."""
        try:
            await self.async_send_command("move_left", angular=speed)
        except Exception as error:
            self.error_handler.handle_error(error, "async_move_left")

    async def async_move_right(self, speed: float) -> None:
        """Move right."""
        try:
            await self.async_send_command("move_right", angular=speed)
        except Exception as error:
            self.error_handler.handle_error(error, "async_move_right")

    async def async_move_back(self, speed: float) -> None:
        """Move back."""
        try:
            await self.async_send_command("move_back", linear=speed)
        except Exception as error:
            self.error_handler.handle_error(error, "async_move_back")

    async def async_rtk_dock_location(self) -> None:
        """RTK and dock location."""
        try:
            await self.async_send_command("allpowerfull_rw", id=5, rw=1, context=1)
        except Exception as error:
            self.error_handler.handle_error(error, "async_rtk_dock_location")

    async def async_request_iot_sync(self, stop: bool = False) -> None:
        """Sync specific info from device."""
        try:
            await self.async_send_command(
                "request_iot_sys",
                rpt_act=RptAct.RPT_STOP if stop else RptAct.RPT_START,
                rpt_info_type=[
                    RptInfoType.RIT_DEV_STA,
                    RptInfoType.RIT_DEV_LOCAL,
                    RptInfoType.RIT_WORK,
                ],
                timeout=10000,
                period=3000,
                no_change_period=4000,
                count=0,
            )
        except Exception as error:
            self.error_handler.handle_error(error, "async_request_iot_sync")

    async def async_send_command(self, command: str, **kwargs: Any) -> None:
        """Send command."""
        try:
            await self.manager.send_command_with_args(
                self.device_name, command, **kwargs
            )
        except SetupException:
            await self.async_login()
        except DeviceOfflineException:
            """Device is offline try bluetooth if we have it."""
            try:
                if self.manager.get_device_by_name(self.device_name).ble():
                    await (
                        self.manager.get_device_by_name(self.device_name)
                        .ble()
                        .queue_command(command, **kwargs)
                    )
            except COMMAND_EXCEPTIONS as exc:
                self.error_handler.handle_error(exc, "async_send_command")
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="command_failed"
                ) from exc
        except Exception as error:
            self.error_handler.handle_error(error, "async_send_command")

    async def async_plan_route(self, operation_settings: OperationSettings) -> None:
        """Plan mow."""
        route_information = GenerateRouteInformation(
            one_hashs=operation_settings.areas,
            rain_tactics=operation_settings.rain_tactics,
            speed=operation_settings.speed,
            ultra_wave=operation_settings.ultra_wave,  # touch no touch etc
            toward=operation_settings.toward,  # is just angle
            toward_included_angle=operation_settings.toward_included_angle,  # angle relative to grid??
            toward_mode=operation_settings.toward_mode,
            blade_height=operation_settings.blade_height,
            channel_mode=operation_settings.channel_mode,  # line mode is grid single double or single2
            channel_width=operation_settings.channel_width,
            job_mode=operation_settings.job_mode,  # taskMode
            edge_mode=operation_settings.border_mode,  # border laps
            path_order=create_path_order(operation_settings, self.device_name),
            obstacle_laps=operation_settings.obstacle_laps,
        )

        try:
            await self.async_send_command(
                "generate_route_information", generate_route_information=route_information
            )
        except Exception as error:
            self.error_handler.handle_error(error, "async_plan_route")

    async def clear_all_maps(self) -> None:
        try:
            data = self.manager.get_device_by_name(self.device_name).mower_state
            data.map = HashList()
        except Exception as error:
            self.error_handler.handle_error(error, "clear_all_maps")

    async def _async_update_notification(self) -> None:
        """Update data from incoming messages."""
        try:
            mower = self.manager.mower(self.device_name)
            self.async_set_updated_data(mower)
        except Exception as error:
            self.error_handler.handle_error(error, "_async_update_notification")

    async def check_firmware_version(self) -> None:
        """Check if firmware version is udpated."""
        try:
            mower = self.manager.mower(self.device_name)
            device_registry = dr.async_get(self.hass)
            device_entry = device_registry.async_get_device(
                identifiers={(DOMAIN, self.device_name)}
            )
            if device_entry is None:
                return

            new_swversion = None
            if len(mower.net.toapp_devinfo_resp.resp_ids) > 0:
                new_swversion = mower.net.toapp_devinfo_resp.resp_ids[0].info

            if new_swversion is not None or new_swversion != device_entry.sw_version:
                device_registry.async_update_device(
                    device_entry.id, sw_version=new_swversion
                )

            model_id = None
            if has_field(mower.sys.device_product_type_info):
                model_id = mower.sys.device_product_type_info.main_product_type

            if model_id is not None or model_id != device_entry.model_id:
                device_registry.async_update_device(device_entry.id, model_id=model_id)
        except Exception as error:
            self.error_handler.handle_error(error, "check_firmware_version")

    async def async_login(self) -> None:
        """Login to cloud servers."""
        try:
            await self.hass.async_add_executor_job(
                self.manager.get_device_by_name(self.device_name).cloud().mqtt.disconnect
            )
            account = self.config_entry.data.get(CONF_ACCOUNTNAME)
            password = self.config_entry.data.get(CONF_PASSWORD)
            await self.manager.login_and_initiate_cloud(account, password, True)
        except Exception as error:
            self.error_handler.handle_error(error, "async_login")

    async def _async_update_data(self) -> MowingDevice:
        """Get data from the device."""
        device = self.manager.get_device_by_name(self.device_name)
        await self.check_firmware_version()

        if self.address:
            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, self.address
            )

            if not ble_device and device.cloud() is None:
                self.update_failures += 1
                self.error_handler.handle_error(
                    Exception("Could not find device"), "_async_update_data"
                )
                raise UpdateFailed("Could not find device")

            if ble_device and ble_device.name == device.name:
                if device.ble() is not None:
                    device.ble().update_device(ble_device)
                else:
                    device.add_ble(ble_device)

        try:
            if (
                len(device.mower_state.net.toapp_devinfo_resp.resp_ids) == 0
                or device.mower_state.net.toapp_wifi_iot_status.productkey is None
            ):
                await self.manager.start_sync(self.device_name, 0)

            await self.async_send_command("get_report_cfg")

        except COMMAND_EXCEPTIONS as exc:
            self.update_failures += 1
            self.error_handler.handle_error(exc, "_async_update_data")
            raise UpdateFailed(f"Updating Mammotion device failed: {exc}") from exc
        except SetupException:
            await self.async_login()
        except DeviceOfflineException:
            """Device is offline try bluetooth if we have it."""
            if device.ble():
                await device.ble().command("get_report_cfg")
            # TODO set a sensor to offline
        except Exception as error:
            self.update_failures += 1
            self.error_handler.handle_error(error, "_async_update_data")
            raise UpdateFailed(f"Updating Mammotion device failed: {error}") from error

        LOGGER.debug("Updated Mammotion device %s", self.device_name)
        LOGGER.debug("================= Debug Log =================")
        LOGGER.debug(
            "Mammotion device data: %s",
            asdict(self.manager.get_device_by_name(self.device_name).mower_state),
        )
        LOGGER.debug("==================================")

        self.update_failures = 0
        data = self.manager.get_device_by_name(self.device_name).mower_state
        await self.async_save_data(data)
        return data

    @property
    def operation_settings(self) -> OperationSettings:
        """Return operation settings for planning."""
        return self._operation_settings

    # TODO when submitting to HA use this 2024.8 and up
    # async def _async_setup(self) -> None:
    #     try:
    #         await self.async_setup()
    #     except COMMAND_EXCEPTIONS as exc:
    #         raise UpdateFailed(f"Setting up Mammotion device failed: {exc}") from exc
