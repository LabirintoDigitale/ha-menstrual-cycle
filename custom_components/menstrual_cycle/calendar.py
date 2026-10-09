"""Calendar for the Menstrual Cycle integration."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEntityFeature,
    CalendarEvent,
)
from homeassistant.components.calendar.const import EVENT_END, EVENT_START
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, EVENT_LABELS, UID_OVULATION_PREFIX, UID_PERIOD_PREFIX
from .coordinator import MenstrualCycleConfigEntry, MenstrualCycleCoordinator, today
from .entity import MenstrualCycleEntity

ONE_DAY = timedelta(days=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MenstrualCycleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the calendar."""
    async_add_entities([MenstrualCycleCalendar(entry.runtime_data)])


def _to_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return dt_util.as_local(value).date()
    return value


class MenstrualCycleCalendar(MenstrualCycleEntity, CalendarEntity):
    """Shows logged periods, expected periods, fertile windows and ovulation."""

    _attr_name = None
    _attr_supported_features = (
        CalendarEntityFeature.CREATE_EVENT | CalendarEntityFeature.DELETE_EVENT
    )

    def __init__(self, coordinator: MenstrualCycleCoordinator) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator, "calendar")

    def _labels(self) -> dict[str, str]:
        return EVENT_LABELS.get(self.hass.config.language[:2], EVENT_LABELS["en"])

    def _all_events(self) -> list[CalendarEvent]:
        data = self.coordinator.data
        labels = self._labels()
        events = [
            CalendarEvent(
                start=period.start,
                end=period.last_day(data.period_length) + ONE_DAY,
                summary=labels["period"],
                uid=f"{UID_PERIOD_PREFIX}{period.start.isoformat()}",
            )
            for period in data.periods
        ]
        events.extend(
            CalendarEvent(
                start=ovulation.estimated,
                end=ovulation.estimated + ONE_DAY,
                summary=labels["logged_ovulation"],
                uid=f"{UID_OVULATION_PREFIX}{ovulation.observed.isoformat()}",
            )
            for ovulation in data.ovulations
        )
        if (prediction := data.prediction) is not None:
            for cycle in (prediction.current_cycle, *prediction.upcoming):
                if cycle is not prediction.current_cycle:
                    events.append(
                        CalendarEvent(
                            start=cycle.period_start,
                            end=cycle.period_end + ONE_DAY,
                            summary=labels["predicted_period"],
                            description=labels["prediction"],
                        )
                    )
                events.append(
                    CalendarEvent(
                        start=cycle.fertile_start,
                        end=cycle.fertile_end + ONE_DAY,
                        summary=labels["fertile"],
                        description=labels["prediction"],
                    )
                )
                if not cycle.ovulation_confirmed:
                    events.append(
                        CalendarEvent(
                            start=cycle.ovulation,
                            end=cycle.ovulation + ONE_DAY,
                            summary=labels["ovulation"],
                            description=labels["prediction"],
                        )
                    )
        events.sort(key=lambda event: (event.start, event.end))
        return events

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming event."""
        now = today()
        return next((e for e in self._all_events() if e.end > now), None)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return the events overlapping the requested range."""
        start = _to_date(start_date)
        end = _to_date(end_date)
        return [e for e in self._all_events() if e.start <= end and e.end > start]

    async def async_create_event(self, **kwargs: Any) -> None:
        """Log a period from the calendar UI."""
        start = kwargs[EVENT_START]
        end = kwargs[EVENT_END]
        if isinstance(start, datetime):
            first, last = _to_date(start), _to_date(end)
        else:
            # All-day events have an exclusive end date.
            first, last = start, end - ONE_DAY
        await self.coordinator.async_add_period(first, max(first, last))

    async def async_delete_event(
        self,
        uid: str,
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        """Delete a logged period or ovulation; predictions can't be deleted."""
        if uid.startswith(UID_OVULATION_PREFIX):
            await self.coordinator.async_delete_ovulation(
                date.fromisoformat(uid.removeprefix(UID_OVULATION_PREFIX))
            )
            return
        if not uid.startswith(UID_PERIOD_PREFIX):
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="cannot_delete_prediction"
            )
        await self.coordinator.async_delete_period(
            date.fromisoformat(uid.removeprefix(UID_PERIOD_PREFIX))
        )
