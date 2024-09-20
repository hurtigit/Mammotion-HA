"""Constants for the Mammotion Luba integration."""

import logging
from typing import final

from bleak.exc import BleakError
from bleak_retry_connector import BleakNotFoundError
from pymammotion.mammotion.devices.mammotion_bluetooth import CharacteristicMissingError

domain: final = "mammotion"

device_support = ("Luba", "Yuka")

attr_direction = "direction"

default_retry_count = 3
conf_retry_count = "retry_count"
logger: final = logging.getLogger(__package__)

command_exceptions = (
    BleakNotFoundError,
    CharacteristicMissingError,
    BleakError,
    TimeoutError,
)

conf_stay_connected_bluetooth: final = "stay_connected_bluetooth"
conf_accountname: final = "account_name"
conf_use_wifi: final = "use_wifi"
conf_device_name: final = "device_name"
conf_auth_data: final = "auth_data"
conf_aep_data: final = "aep_data"
conf_session_data: final = "session_data"
conf_region_data: final = "region_data"
conf_device_data: final = "device_data"
