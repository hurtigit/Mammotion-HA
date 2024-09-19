"""Automation capabilities for the Mammotion integration."""

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.script import Script
from homeassistant.helpers.service import async_call_from_config

from .const import DOMAIN
from .error_handling import MammotionErrorHandling

AUTOMATION_SCHEMA = {
    "trigger": list,
    "condition": list,
    "action": list,
}


class MammotionAutomation:
    """Class to handle automations for the Mammotion integration."""

    def __init__(self, hass: HomeAssistant, config: dict):
        """Initialize the automation."""
        self.hass = hass
        self.config = config
        self.script = Script(hass, config.get("action", []), DOMAIN)
        self._remove_listener = None
        self.error_handler = MammotionErrorHandling(hass)

    async def async_enable(self):
        """Enable the automation."""
        try:
            self._remove_listener = async_track_state_change_event(
                self.hass, self.config.get("trigger", []), self._handle_trigger
            )
        except Exception as error:
            self.error_handler.handle_error(error, "async_enable")

    async def async_disable(self):
        """Disable the automation."""
        try:
            if self._remove_listener:
                self._remove_listener()
                self._remove_listener = None
        except Exception as error:
            self.error_handler.handle_error(error, "async_disable")

    @callback
    async def _handle_trigger(self, event):
        """Handle the trigger event."""
        try:
            if all(
                await self.hass.helpers.condition.async_condition(self.config.get("condition", []))
            ):
                await self.script.async_run(context=event.context)
        except Exception as error:
            self.error_handler.handle_error(error, "_handle_trigger")

    async def async_update(self, config: dict):
        """Update the automation configuration."""
        try:
            await self.async_disable()
            self.config = config
            self.script = Script(self.hass, config.get("action", []), DOMAIN)
            await self.async_enable()
        except Exception as error:
            self.error_handler.handle_error(error, "async_update")


async def async_setup_automations(hass: HomeAssistant, config: dict):
    """Set up automations for the Mammotion integration."""
    automations = []
    error_handler = MammotionErrorHandling(hass)
    try:
        for automation_config in config.get("automations", []):
            automation = MammotionAutomation(hass, automation_config)
            await automation.async_enable()
            automations.append(automation)
    except Exception as error:
        error_handler.handle_error(error, "async_setup_automations")
    return automations


async def async_unload_automations(automations):
    """Unload automations for the Mammotion integration."""
    error_handler = MammotionErrorHandling(hass)
    try:
        for automation in automations:
            await automation.async_disable()
    except Exception as error:
        error_handler.handle_error(error, "async_unload_automations")
