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
    SensorStateClass,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .calculator import Phase, Prediction, card_attributes
from .coordinator import MenstrualCycleConfigEntry, MenstrualCycleCoordinator
from .entity import MenstrualCycleEntity


@dataclass(frozen=True, kw_only=True)
class MenstrualCycleSensorEntityDescription(SensorEntityDescription):
    """Describes a Menstrual Cycle sensor."""

    value_fn: Callable[[Prediction], date | float | int | str | None]
    attributes_fn: Callable[[Prediction], dict[str, Any]] | None = None


def _ovulation_attributes(prediction: Prediction) -> dict[str, Any]:
    """How the ovulation date was obtained and how uncertain it is."""
    return {
        "confirmed": prediction.next_ovulation_confirmed,
        "variability_days": prediction.ovulation_sd,
        "fertile_window_margin_days": 0
        if prediction.next_ovulation_confirmed
        else prediction.fertile_margin,
        "luteal_phase_days": prediction.luteal_length,
    }


def _history_attributes(prediction: Prediction) -> dict[str, Any]:
    """The recent completed cycles, for analysis."""
    return {
        "cycles_used": prediction.cycles_used,
        "variability_days": prediction.cycle_length_sd,
        "cycles": [
            {
                "start": record.start.isoformat(),
                "length": record.length,
                "period_length": record.period_length,
                "ovulation": record.ovulation.isoformat() if record.ovulation else None,
                "follicular_length": record.follicular_length,
                "luteal_length": record.luteal_length,
            }
            for record in prediction.history
        ],
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
        attributes_fn=_ovulation_attributes,
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
        attributes_fn=card_attributes,
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
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda p: p.cycle_length,
        attributes_fn=_history_attributes,
    ),
    MenstrualCycleSensorEntityDescription(
        key="average_period_length",
        translation_key="average_period_length",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda p: p.period_length,
    ),
    MenstrualCycleSensorEntityDescription(
        key="luteal_phase_length",
        translation_key="luteal_phase_length",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda p: p.luteal_length,
        attributes_fn=lambda p: {"logged_ovulations": p.luteal_samples},
    ),
    MenstrualCycleSensorEntityDescription(
        key="follicular_phase_length",
        translation_key="follicular_phase_length",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda p: p.follicular_length,
    ),
    MenstrualCycleSensorEntityDescription(
        key="cycle_length_variability",
        translation_key="cycle_length_variability",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda p: p.cycle_length_sd,
    ),
    MenstrualCycleSensorEntityDescription(
        key="ovulation_variability",
        translation_key="ovulation_variability",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda p: p.ovulation_sd,
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
    # The cycle history is already in the store: don't copy it into the
    # recorder database at every state change.
    _unrecorded_attributes = frozenset({"cycles"})

    def __init__(
        self,
        coordinator: MenstrualCycleCoordinator,
        description: MenstrualCycleSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> date | float | int | str | None:
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
