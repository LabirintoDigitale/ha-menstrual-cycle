"""Sensors for the Menstrual Cycle integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .calculator import Phase, Prediction
from .coordinator import MenstrualCycleConfigEntry, MenstrualCycleCoordinator
from .entity import MenstrualCycleEntity


@dataclass(frozen=True, kw_only=True)
class MenstrualCycleSensorEntityDescription(SensorEntityDescription):
    """Describes a Menstrual Cycle sensor."""

    value_fn: Callable[[Prediction], date | int | str]


SENSORS: tuple[MenstrualCycleSensorEntityDescription, ...] = (
    MenstrualCycleSensorEntityDescription(
        key="next_period",
        translation_key="next_period",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda p: p.next_period_start,
    ),
    MenstrualCycleSensorEntityDescription(
        key="days_until_next_period",
        translation_key="days_until_next_period",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda p: p.days_until_next_period,
    ),
    MenstrualCycleSensorEntityDescription(
        key="ovulation",
        translation_key="ovulation",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda p: p.next_ovulation,
    ),
    MenstrualCycleSensorEntityDescription(
        key="fertile_window_start",
        translation_key="fertile_window_start",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda p: p.next_fertile_start,
    ),
    MenstrualCycleSensorEntityDescription(
        key="fertile_window_end",
        translation_key="fertile_window_end",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda p: p.next_fertile_end,
    ),
    MenstrualCycleSensorEntityDescription(
        key="phase",
        translation_key="phase",
        device_class=SensorDeviceClass.ENUM,
        options=[phase.value for phase in Phase],
        value_fn=lambda p: p.phase.value,
    ),
    MenstrualCycleSensorEntityDescription(
        key="cycle_day",
        translation_key="cycle_day",
        value_fn=lambda p: p.cycle_day,
    ),
    MenstrualCycleSensorEntityDescription(
        key="last_period",
        translation_key="last_period",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda p: p.last_period.start,
    ),
    MenstrualCycleSensorEntityDescription(
        key="average_cycle_length",
        translation_key="average_cycle_length",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda p: p.cycle_length,
    ),
    MenstrualCycleSensorEntityDescription(
        key="average_period_length",
        translation_key="average_period_length",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda p: p.period_length,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MenstrualCycleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    async_add_entities(
        MenstrualCycleSensor(entry.runtime_data, description) for description in SENSORS
    )


class MenstrualCycleSensor(MenstrualCycleEntity, SensorEntity):
    """A value derived from the cycle prediction."""

    entity_description: MenstrualCycleSensorEntityDescription

    def __init__(
        self,
        coordinator: MenstrualCycleCoordinator,
        description: MenstrualCycleSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> date | int | str | None:
        """Return the value, or None until a period is logged."""
        if (prediction := self.coordinator.data.prediction) is None:
            return None
        return self.entity_description.value_fn(prediction)
