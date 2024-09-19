"""Mapping and zone management for the Mammotion integration."""

from typing import Any, Dict, List
from .error_handling import MammotionErrorHandling

class Zone:
    def __init__(self, zone_id: str, name: str, coordinates: List[Dict[str, Any]]):
        self.zone_id = zone_id
        self.name = name
        self.coordinates = coordinates

class MappingManager:
    def __init__(self, hass):
        self.zones: Dict[str, Zone] = {}
        self.error_handler = MammotionErrorHandling(hass)

    def create_zone(self, zone_id: str, name: str, coordinates: List[Dict[str, Any]]):
        try:
            if zone_id in self.zones:
                raise ValueError(f"Zone with ID {zone_id} already exists.")
            self.zones[zone_id] = Zone(zone_id, name, coordinates)
        except Exception as error:
            self.error_handler.handle_error(error, "create_zone")

    def update_zone(self, zone_id: str, name: str = None, coordinates: List[Dict[str, Any]] = None):
        try:
            if zone_id not in self.zones:
                raise ValueError(f"Zone with ID {zone_id} does not exist.")
            if name:
                self.zones[zone_id].name = name
            if coordinates:
                self.zones[zone_id].coordinates = coordinates
        except Exception as error:
            self.error_handler.handle_error(error, "update_zone")

    def delete_zone(self, zone_id: str):
        try:
            if zone_id not in self.zones:
                raise ValueError(f"Zone with ID {zone_id} does not exist.")
            del self.zones[zone_id]
        except Exception as error:
            self.error_handler.handle_error(error, "delete_zone")

    def get_zone(self, zone_id: str) -> Zone:
        try:
            if zone_id not in self.zones:
                raise ValueError(f"Zone with ID {zone_id} does not exist.")
            return self.zones[zone_id]
        except Exception as error:
            self.error_handler.handle_error(error, "get_zone")
            return None

    def list_zones(self) -> List[Zone]:
        try:
            return list(self.zones.values())
        except Exception as error:
            self.error_handler.handle_error(error, "list_zones")
            return []
