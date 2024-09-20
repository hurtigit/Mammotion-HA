import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.util.dt import utcnow

from custom_components.mammotion.scheduler import MammotionScheduler
from custom_components.mammotion.coordinator import MammotionDataUpdateCoordinator
from custom_components.mammotion.error_handling import MammotionErrorHandling


class TestMammotionScheduler(unittest.TestCase):
    def setUp(self):
        self.hass = MagicMock(spec=HomeAssistant)
        self.coordinator = MagicMock(spec=MammotionDataUpdateCoordinator)
        self.scheduler = MammotionScheduler(self.hass, self.coordinator)
        self.error_handler = MammotionErrorHandling(self.hass)

    def test_add_schedule(self):
        start_time = utcnow() + timedelta(seconds=1)
        end_time = start_time + timedelta(minutes=30)
        task = "start_mowing"
        kwargs = {"area": "front_yard"}

        try:
            self.scheduler.add_schedule(start_time, end_time, task, **kwargs)
            self.assertEqual(len(self.scheduler.schedules), 1)
            self.assertEqual(self.scheduler.schedules[0]["task"], task)
            self.assertEqual(self.scheduler.schedules[0]["kwargs"], kwargs)
        except Exception as error:
            self.error_handler.handle_error(error, "test_add_schedule")

    def test_remove_schedule(self):
        start_time = utcnow() + timedelta(seconds=1)
        end_time = start_time + timedelta(minutes=30)
        task = "start_mowing"
        kwargs = {"area": "front_yard"}

        try:
            self.scheduler.add_schedule(start_time, end_time, task, **kwargs)
            self.scheduler.remove_schedule(0)
            self.assertEqual(len(self.scheduler.schedules), 0)
        except Exception as error:
            self.error_handler.handle_error(error, "test_remove_schedule")

    def test_modify_schedule(self):
        start_time = utcnow() + timedelta(seconds=1)
        end_time = start_time + timedelta(minutes=30)
        task = "start_mowing"
        kwargs = {"area": "front_yard"}

        try:
            self.scheduler.add_schedule(start_time, end_time, task, **kwargs)
            new_start_time = start_time + timedelta(minutes=10)
            new_end_time = end_time + timedelta(minutes=10)
            new_task = "stop_mowing"
            new_kwargs = {"area": "back_yard"}

            self.scheduler.modify_schedule(0, new_start_time, new_end_time, new_task, **new_kwargs)
            self.assertEqual(self.scheduler.schedules[0]["start_time"], new_start_time)
            self.assertEqual(self.scheduler.schedules[0]["end_time"], new_end_time)
            self.assertEqual(self.scheduler.schedules[0]["task"], new_task)
            self.assertEqual(self.scheduler.schedules[0]["kwargs"], new_kwargs)
        except Exception as error:
            self.error_handler.handle_error(error, "test_modify_schedule")

    @patch("custom_components.mammotion.scheduler.async_track_point_in_utc_time")
    def test_schedule_task(self, mock_async_track_point_in_utc_time):
        start_time = utcnow() + timedelta(seconds=1)
        end_time = start_time + timedelta(minutes=30)
        task = "start_mowing"
        kwargs = {"area": "front_yard"}

        try:
            self.scheduler.add_schedule(start_time, end_time, task, **kwargs)
            self.assertEqual(mock_async_track_point_in_utc_time.call_count, 2)
            self.assertEqual(mock_async_track_point_in_utc_time.call_args_list[0][0][1].__name__, "start_task")
            self.assertEqual(mock_async_track_point_in_utc_time.call_args_list[1][0][1].__name__, "stop_task")
        except Exception as error:
            self.error_handler.handle_error(error, "test_schedule_task")

    def test_get_schedules(self):
        start_time = utcnow() + timedelta(seconds=1)
        end_time = start_time + timedelta(minutes=30)
        task = "start_mowing"
        kwargs = {"area": "front_yard"}

        try:
            self.scheduler.add_schedule(start_time, end_time, task, **kwargs)
            schedules = self.scheduler.get_schedules()
            self.assertEqual(len(schedules), 1)
            self.assertEqual(schedules[0]["task"], task)
            self.assertEqual(schedules[0]["kwargs"], kwargs)
        except Exception as error:
            self.error_handler.handle_error(error, "test_get_schedules")

    def test_add_multiple_schedules(self):
        start_time_1 = utcnow() + timedelta(seconds=1)
        end_time_1 = start_time_1 + timedelta(minutes=30)
        task_1 = "start_mowing"
        kwargs_1 = {"area": "front_yard"}

        start_time_2 = utcnow() + timedelta(seconds=2)
        end_time_2 = start_time_2 + timedelta(minutes=40)
        task_2 = "stop_mowing"
        kwargs_2 = {"area": "back_yard"}

        try:
            self.scheduler.add_schedule(start_time_1, end_time_1, task_1, **kwargs_1)
            self.scheduler.add_schedule(start_time_2, end_time_2, task_2, **kwargs_2)
            self.assertEqual(len(self.scheduler.schedules), 2)
            self.assertEqual(self.scheduler.schedules[0]["task"], task_1)
            self.assertEqual(self.scheduler.schedules[0]["kwargs"], kwargs_1)
            self.assertEqual(self.scheduler.schedules[1]["task"], task_2)
            self.assertEqual(self.scheduler.schedules[1]["kwargs"], kwargs_2)
        except Exception as error:
            self.error_handler.handle_error(error, "test_add_multiple_schedules")

    def test_remove_non_existent_schedule(self):
        try:
            self.scheduler.remove_schedule(0)
            self.assertEqual(len(self.scheduler.schedules), 0)
        except Exception as error:
            self.error_handler.handle_error(error, "test_remove_non_existent_schedule")

    def test_modify_non_existent_schedule(self):
        new_start_time = utcnow() + timedelta(minutes=10)
        new_end_time = new_start_time + timedelta(minutes=10)
        new_task = "stop_mowing"
        new_kwargs = {"area": "back_yard"}

        try:
            self.scheduler.modify_schedule(0, new_start_time, new_end_time, new_task, **new_kwargs)
            self.assertEqual(len(self.scheduler.schedules), 0)
        except Exception as error:
            self.error_handler.handle_error(error, "test_modify_non_existent_schedule")


if __name__ == "__main__":
    unittest.main()
