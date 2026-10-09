"""Binary sensors for the Menstrual Cycle integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .calculator import Prediction
from .coordinator import MenstrualCycleConfigEntry, MenstrualCycleCoordinator
from .entity import MenstrualCycleEntity


@dataclass(frozen=True, kw_only=True)
class MenstrualCycleBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Menstrual Cycle binary sensor."""

    is_on_fn: Callable[[Prediction], bool]


BINARY_SENSORS: tuple[MenstrualCycleBinarySensorEntityDescription, ...] = (
    MenstrualCycleBinarySensorEntityDescription(
        key="period",
        translation_key="period",
        is_on_fn=lambda p: p.in_period,
    ),
    MenstrualCycleBinarySensorEntityDescription(
        key="fertile",
        translation_key="fertile",
        is_on_fn=lambda p: p.in_fertile_window,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MenstrualCycleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    async_add_entities(
        MenstrualCycleBinarySensor(entry.runtime_data, description)
        for description in BINARY_SENSORS
    )


class MenstrualCycleBinarySensor(MenstrualCycleEntity, BinarySensorEntity):
    """Whether today falls in a given part of the cycle."""

    entity_description: MenstrualCycleBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: MenstrualCycleCoordinator,
        description: MenstrualCycleBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the state, or None until a period is logged."""
        if (prediction := self.coordinator.data.prediction) is None:
            return None
        return self.entity_description.is_on_fn(prediction)
