"""Sensors for the Menstrual Cycle integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

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
    attributes_fn: Callable[[Prediction], dict[str, Any]] | None = None


def _cycle_attributes(prediction: Prediction) -> dict[str, Any]:
    """Describe the current cycle as day numbers, for the dashboard card."""
    cycle = prediction.current_cycle
    start = prediction.last_period.start

    def day(value: date) -> int:
        return (value - start).days + 1

    return {
        "cycle_length": prediction.cycle_length,
        "period_length": day(prediction.last_period.last_day(prediction.period_length)),
        "fertile_start_day": day(cycle.fertile_start),
        "ovulation_day": day(cycle.ovulation),
        "fertile_end_day": day(cycle.fertile_end),
        "phase": prediction.phase.value,
        "next_period": prediction.next_period_start.isoformat(),
        "days_until_next_period": prediction.days_until_next_period,
    }


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
        attributes_fn=_cycle_attributes,
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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes, if the sensor has any."""
        attributes_fn = self.entity_description.attributes_fn
        if attributes_fn is None or (prediction := self.coordinator.data.prediction) is None:
            return None
        return attributes_fn(prediction)
