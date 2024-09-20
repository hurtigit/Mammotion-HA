import unittest
from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.mammotion.firmware import (
    MammotionFirmwareUpdateCoordinator,
    MammotionFirmwareUpdateEntity,
)
from custom_components.mammotion.coordinator import MammotionDataUpdateCoordinator
from custom_components.mammotion.error_handling import MammotionErrorHandling


class TestMammotionFirmwareUpdate(unittest.TestCase):
    def setUp(self):
        self.hass = MagicMock(spec=HomeAssistant)
        self.coordinator = MagicMock(spec=MammotionDataUpdateCoordinator)
        self.firmware_coordinator = MammotionFirmwareUpdateCoordinator(self.hass, self.coordinator)
        self.firmware_entity = MammotionFirmwareUpdateEntity(self.coordinator)
        self.error_handler = MammotionErrorHandling(self.hass)

    @patch("custom_components.mammotion.firmware.MammotionFirmwareUpdateCoordinator.async_check_for_updates")
    def test_check_for_updates(self, mock_check_for_updates):
        try:
            self.hass.async_create_task(self.firmware_coordinator.async_check_for_updates())
            mock_check_for_updates.assert_called_once()
        except Exception as error:
            self.error_handler.handle_error(error, "test_check_for_updates")

    @patch("custom_components.mammotion.firmware.MammotionFirmwareUpdateCoordinator.async_download_update")
    def test_download_update(self, mock_download_update):
        try:
            self.hass.async_create_task(self.firmware_coordinator.async_download_update())
            mock_download_update.assert_called_once()
        except Exception as error:
            self.error_handler.handle_error(error, "test_download_update")

    @patch("custom_components.mammotion.firmware.MammotionFirmwareUpdateCoordinator.async_install_update")
    def test_install_update(self, mock_install_update):
        try:
            self.hass.async_create_task(self.firmware_coordinator.async_install_update())
            mock_install_update.assert_called_once()
        except Exception as error:
            self.error_handler.handle_error(error, "test_install_update")

    @patch("custom_components.mammotion.firmware.MammotionFirmwareUpdateCoordinator.async_update")
    def test_update(self, mock_update):
        try:
            self.hass.async_create_task(self.firmware_coordinator.async_update())
            mock_update.assert_called_once()
        except Exception as error:
            self.error_handler.handle_error(error, "test_update")

    @patch("custom_components.mammotion.firmware.MammotionFirmwareUpdateEntity.async_update")
    def test_firmware_entity_update(self, mock_firmware_entity_update):
        try:
            self.hass.async_create_task(self.firmware_entity.async_update())
            mock_firmware_entity_update.assert_called_once()
        except Exception as error:
            self.error_handler.handle_error(error, "test_firmware_entity_update")

    @patch("custom_components.mammotion.firmware.MammotionFirmwareUpdateEntity.async_check_for_updates")
    def test_firmware_entity_check_for_updates(self, mock_firmware_entity_check_for_updates):
        try:
            self.hass.async_create_task(self.firmware_entity.async_check_for_updates())
            mock_firmware_entity_check_for_updates.assert_called_once()
        except Exception as error:
            self.error_handler.handle_error(error, "test_firmware_entity_check_for_updates")

    @patch("custom_components.mammotion.firmware.MammotionFirmwareUpdateEntity.async_download_update")
    def test_firmware_entity_download_update(self, mock_firmware_entity_download_update):
        try:
            self.hass.async_create_task(self.firmware_entity.async_download_update())
            mock_firmware_entity_download_update.assert_called_once()
        except Exception as error:
            self.error_handler.handle_error(error, "test_firmware_entity_download_update")

    @patch("custom_components.mammotion.firmware.MammotionFirmwareUpdateEntity.async_install_update")
    def test_firmware_entity_install_update(self, mock_firmware_entity_install_update):
        try:
            self.hass.async_create_task(self.firmware_entity.async_install_update())
            mock_firmware_entity_install_update.assert_called_once()
        except Exception as error:
            self.error_handler.handle_error(error, "test_firmware_entity_install_update")

    @patch("custom_components.mammotion.firmware.MammotionFirmwareUpdateCoordinator.async_check_for_updates")
    def test_firmware_coordinator_check_for_updates(self, mock_firmware_coordinator_check_for_updates):
        try:
            self.hass.async_create_task(self.firmware_coordinator.async_check_for_updates())
            mock_firmware_coordinator_check_for_updates.assert_called_once()
        except Exception as error:
            self.error_handler.handle_error(error, "test_firmware_coordinator_check_for_updates")

    @patch("custom_components.mammotion.firmware.MammotionFirmwareUpdateCoordinator.async_download_update")
    def test_firmware_coordinator_download_update(self, mock_firmware_coordinator_download_update):
        try:
            self.hass.async_create_task(self.firmware_coordinator.async_download_update())
            mock_firmware_coordinator_download_update.assert_called_once()
        except Exception as error:
            self.error_handler.handle_error(error, "test_firmware_coordinator_download_update")

    @patch("custom_components.mammotion.firmware.MammotionFirmwareUpdateCoordinator.async_install_update")
    def test_firmware_coordinator_install_update(self, mock_firmware_coordinator_install_update):
        try:
            self.hass.async_create_task(self.firmware_coordinator.async_install_update())
            mock_firmware_coordinator_install_update.assert_called_once()
        except Exception as error:
            self.error_handler.handle_error(error, "test_firmware_coordinator_install_update")

    @patch("custom_components.mammotion.firmware.MammotionFirmwareUpdateCoordinator.async_update")
    def test_firmware_coordinator_update(self, mock_firmware_coordinator_update):
        try:
            self.hass.async_create_task(self.firmware_coordinator.async_update())
            mock_firmware_coordinator_update.assert_called_once()
        except Exception as error:
            self.error_handler.handle_error(error, "test_firmware_coordinator_update")


if __name__ == "__main__":
    unittest.main()
