from dataclasses import dataclass
from typing import Any, Awaitable, Callable, cast

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from pymammotion.proto.mctrl_nav import AreaHashName
from pymammotion.utility.device_type import DeviceType

from . import MammotionConfigEntry
from .coordinator import MammotionDataUpdateCoordinator
from .entity import MammotionBaseEntity
from .error_handling import MammotionErrorHandling


@dataclass(frozen=True, kw_only=True)
class MammotionSwitchEntityDescription(SwitchEntityDescription):
    """Describes Mammotion switch entity."""

    key: str
    set_fn: Callable[[MammotionDataUpdateCoordinator, bool], Awaitable[None]]


@dataclass(frozen=True, kw_only=True)
class MammotionConfigSwitchEntityDescription(SwitchEntityDescription):
    """Describes Mammotion Config switch entity."""

    key: str
    set_fn: Callable[[MammotionDataUpdateCoordinator, bool], None]


@dataclass(frozen=True, kw_only=True)
class MammotionConfigAreaSwitchEntityDescription(SwitchEntityDescription):
    """Describes the Areas  entities."""

    key: str
    area: int
    set_fn: Callable[[MammotionDataUpdateCoordinator, bool, int], None]


YUKA_CONFIG_SWITCH_ENTITIES: tuple[MammotionConfigSwitchEntityDescription, ...] = (
    MammotionConfigSwitchEntityDescription(
        key="mowing_on_off",
        set_fn=lambda coordinator, value: setattr(
            coordinator.operation_settings, "is_mow", value
        ),
    ),
    MammotionConfigSwitchEntityDescription(
        key="dump_grass_on_off",
        set_fn=lambda coordinator, value: setattr(
            coordinator.operation_settings, "is_dump", value
        ),
    ),
    MammotionConfigSwitchEntityDescription(
        key="edge_on_off",
        set_fn=lambda coordinator, value: setattr(
            coordinator.operation_settings, "is_edge", value
        ),
    ),
)

SWITCH_ENTITIES: tuple[MammotionSwitchEntityDescription, ...] = (
    MammotionSwitchEntityDescription(
        key="blades_on_off",
        set_fn=lambda coordinator, value: coordinator.async_start_stop_blades(value),
    ),
    MammotionSwitchEntityDescription(
        key="side_led_on_off",
        set_fn=lambda coordinator, value: coordinator.async_set_sidelight(int(value)),
    ),
)

CONFIG_SWITCH_ENTITIES: tuple[MammotionConfigSwitchEntityDescription, ...] = (
    MammotionConfigSwitchEntityDescription(
        key="rain_detection_on_off",
        set_fn=lambda coordinator, value: setattr(
            coordinator.operation_settings, "rain_tactics", cast(value, int)
        ),
    ),
)


# Example setup usage
async def async_setup_entry(
    hass: HomeAssistant, entry: MammotionConfigEntry, async_add_entities: Callable
) -> None:
    """Set up the Mammotion switch entities."""
    coordinator = entry.runtime_data
    added_areas: set[str] = set()
    error_handler = MammotionErrorHandling(hass)

    @callback
    def add_entities() -> None:
        """Handle addition of mowing areas."""
        try:
            switch_entities: list[MammotionConfigAreaSwitchEntity] = []
            areas = coordinator.data.map.area.keys()
            area_name = coordinator.data.map.area_name
            new_areas = areas - added_areas
            if new_areas:
                for area_id in new_areas:
                    existing_name: AreaHashName = next(
                        (area for area in area_name if area.hash.__str__() == area_id), None
                    )
                    name = existing_name.name if existing_name else f"mowing area {area_id}"
                    base_area_switch_entity = MammotionConfigAreaSwitchEntityDescription(
                        key=f"{area_id}",
                        area=area_id,
                        name=f"{name}",
                        set_fn=lambda coord,
                        bool_val,
                        value: coord.operation_settings.areas.append(value)
                        if bool_val
                        else coord.operation_settings.areas.remove(value),
                    )
                    switch_entities.append(
                        MammotionConfigAreaSwitchEntity(
                            coordinator,
                            base_area_switch_entity,
                        )
                    )
                    added_areas.add(area_id)

            if switch_entities:
                async_add_entities(switch_entities)
        except Exception as error:
            error_handler.handle_error(error, "add_entities")

    add_entities()
    coordinator.async_add_listener(add_entities)

    entities = []
    try:
        for entity_description in SWITCH_ENTITIES:
            entity = MammotionSwitchEntity(coordinator, entity_description)
            entities.append(entity)

        for entity_description in CONFIG_SWITCH_ENTITIES:
            config_entity = MammotionConfigSwitchEntity(coordinator, entity_description)
            entities.append(config_entity)

        if DeviceType.is_yuka(coordinator.device_name):
            for entity_description in YUKA_CONFIG_SWITCH_ENTITIES:
                config_entity = MammotionConfigSwitchEntity(coordinator, entity_description)
                entities.append(config_entity)
        async_add_entities(entities)
    except Exception as error:
        error_handler.handle_error(error, "async_setup_entry")


class MammotionSwitchEntity(MammotionBaseEntity, SwitchEntity):
    entity_description: MammotionSwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MammotionDataUpdateCoordinator,
        entity_description: MammotionSwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator, entity_description.key)
        self.coordinator = coordinator
        self.entity_description = entity_description
        self._attr_translation_key = entity_description.key
        self._attr_is_on = False  # Default state

    async def async_turn_on(self, **kwargs: Any) -> None:
        error_handler = MammotionErrorHandling(self.hass)
        try:
            self._attr_is_on = True
            await self.entity_description.set_fn(self.coordinator, True)
            self.async_write_ha_state()
        except Exception as error:
            error_handler.handle_error(error, "async_turn_on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        error_handler = MammotionErrorHandling(self.hass)
        try:
            self._attr_is_on = False
            await self.entity_description.set_fn(self.coordinator, False)
            self.async_write_ha_state()
        except Exception as error:
            error_handler.handle_error(error, "async_turn_off")

    async def async_update(self) -> None:
        """Update the entity state."""


class MammotionConfigSwitchEntity(MammotionBaseEntity, SwitchEntity, RestoreEntity):
    entity_description: MammotionConfigSwitchEntityDescription
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: MammotionDataUpdateCoordinator,
        entity_description: MammotionConfigSwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator, entity_description.key)
        self.coordinator = coordinator
        self.entity_description = entity_description
        self._attr_translation_key = entity_description.key
        # TODO grab defaults from operation_settings
        self._attr_is_on = False  # Default state

    async def async_turn_on(self, **kwargs: Any) -> None:
        error_handler = MammotionErrorHandling(self.hass)
        try:
            self._attr_is_on = True
            self.entity_description.set_fn(self.coordinator, True)
            self.async_write_ha_state()
        except Exception as error:
            error_handler.handle_error(error, "async_turn_on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        error_handler = MammotionErrorHandling(self.hass)
        try:
            self._attr_is_on = False
            self.entity_description.set_fn(self.coordinator, False)
            self.async_write_ha_state()
        except Exception as error:
            error_handler.handle_error(error, "async_turn_off")

    async def async_update(self) -> None:
        """Update the entity state."""


class MammotionConfigAreaSwitchEntity(MammotionBaseEntity, SwitchEntity, RestoreEntity):
    entity_description: MammotionConfigAreaSwitchEntityDescription
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: MammotionDataUpdateCoordinator,
        entity_description: MammotionConfigAreaSwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator, entity_description.key)
        self.coordinator = coordinator
        self.entity_description = entity_description
        self._attr_translation_key = entity_description.key
        self._attr_extra_state_attributes = {"hash": entity_description.area}
        # TODO grab defaults from operation_settings
        self._attr_is_on = False  # Default state

    async def async_turn_on(self, **kwargs: Any) -> None:
        error_handler = MammotionErrorHandling(self.hass)
        try:
            self._attr_is_on = True
            self.entity_description.set_fn(
                self.coordinator, True, self.entity_description.area
            )
            self.async_write_ha_state()
        except Exception as error:
            error_handler.handle_error(error, "async_turn_on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        error_handler = MammotionErrorHandling(self.hass)
        try:
            self._attr_is_on = False
            self.entity_description.set_fn(
                self.coordinator, False, self.entity_description.area
            )
            self.async_write_ha_state()
        except Exception as error:
            error_handler.handle_error(error, "async_turn_off")

    async def async_update(self) -> None:
        """Update the entity state."""
