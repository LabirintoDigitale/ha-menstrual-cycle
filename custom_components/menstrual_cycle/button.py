"""Buttons for the Menstrual Cycle integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import MenstrualCycleConfigEntry, MenstrualCycleCoordinator, today
from .entity import MenstrualCycleEntity


@dataclass(frozen=True, kw_only=True)
class MenstrualCycleButtonEntityDescription(ButtonEntityDescription):
    """Describes a Menstrual Cycle button."""

    press_fn: Callable[[MenstrualCycleCoordinator, date], Awaitable[None]]


BUTTONS: tuple[MenstrualCycleButtonEntityDescription, ...] = (
    MenstrualCycleButtonEntityDescription(
        key="period_started",
        translation_key="period_started",
        press_fn=lambda c, day: c.async_log_period_start(day),
    ),
    MenstrualCycleButtonEntityDescription(
        key="period_ended",
        translation_key="period_ended",
        press_fn=lambda c, day: c.async_log_period_end(day),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MenstrualCycleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the buttons."""
    async_add_entities(
        MenstrualCycleButton(entry.runtime_data, description) for description in BUTTONS
    )


class MenstrualCycleButton(MenstrualCycleEntity, ButtonEntity):
    """Logs today as the start or end of a period."""

    entity_description: MenstrualCycleButtonEntityDescription

    def __init__(
        self,
        coordinator: MenstrualCycleCoordinator,
        description: MenstrualCycleButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Log today."""
        await self.entity_description.press_fn(self.coordinator, today())
