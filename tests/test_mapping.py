import unittest
from unittest.mock import MagicMock

from custom_components.mammotion.mapping import MappingManager, Zone
from custom_components.mammotion.error_handling import MammotionErrorHandling


class TestMappingManager(unittest.TestCase):
    def setUp(self):
        self.hass = MagicMock()
        self.mapping_manager = MappingManager(self.hass)
        self.error_handler = MammotionErrorHandling(self.hass)

    def test_create_zone(self):
        zone_id = "zone_1"
        name = "Front Yard"
        coordinates = [{"x": 1, "y": 1}, {"x": 2, "y": 2}]

        try:
            self.mapping_manager.create_zone(zone_id, name, coordinates)
            zone = self.mapping_manager.get_zone(zone_id)

            self.assertEqual(zone.zone_id, zone_id)
            self.assertEqual(zone.name, name)
            self.assertEqual(zone.coordinates, coordinates)
        except Exception as error:
            self.error_handler.handle_error(error, "test_create_zone")

    def test_update_zone(self):
        zone_id = "zone_1"
        name = "Front Yard"
        coordinates = [{"x": 1, "y": 1}, {"x": 2, "y": 2}]

        try:
            self.mapping_manager.create_zone(zone_id, name, coordinates)

            new_name = "Back Yard"
            new_coordinates = [{"x": 3, "y": 3}, {"x": 4, "y": 4}]
            self.mapping_manager.update_zone(zone_id, new_name, new_coordinates)
            zone = self.mapping_manager.get_zone(zone_id)

            self.assertEqual(zone.name, new_name)
            self.assertEqual(zone.coordinates, new_coordinates)
        except Exception as error:
            self.error_handler.handle_error(error, "test_update_zone")

    def test_delete_zone(self):
        zone_id = "zone_1"
        name = "Front Yard"
        coordinates = [{"x": 1, "y": 1}, {"x": 2, "y": 2}]

        try:
            self.mapping_manager.create_zone(zone_id, name, coordinates)
            self.mapping_manager.delete_zone(zone_id)

            with self.assertRaises(ValueError):
                self.mapping_manager.get_zone(zone_id)
        except Exception as error:
            self.error_handler.handle_error(error, "test_delete_zone")

    def test_list_zones(self):
        zone_id_1 = "zone_1"
        name_1 = "Front Yard"
        coordinates_1 = [{"x": 1, "y": 1}, {"x": 2, "y": 2}]

        zone_id_2 = "zone_2"
        name_2 = "Back Yard"
        coordinates_2 = [{"x": 3, "y": 3}, {"x": 4, "y": 4}]

        try:
            self.mapping_manager.create_zone(zone_id_1, name_1, coordinates_1)
            self.mapping_manager.create_zone(zone_id_2, name_2, coordinates_2)

            zones = self.mapping_manager.list_zones()

            self.assertEqual(len(zones), 2)
            self.assertEqual(zones[0].zone_id, zone_id_1)
            self.assertEqual(zones[1].zone_id, zone_id_2)
        except Exception as error:
            self.error_handler.handle_error(error, "test_list_zones")


if __name__ == "__main__":
    unittest.main()
