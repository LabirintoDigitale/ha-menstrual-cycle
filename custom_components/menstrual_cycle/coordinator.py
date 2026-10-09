"""Storage and state for the Menstrual Cycle integration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .calculator import (
    MAX_PERIOD_LENGTH,
    Ovulation,
    OvulationMethod,
    Period,
    Prediction,
    predict,
)
from .const import (
    CONF_CYCLE_LENGTH,
    CONF_FORECAST_CYCLES,
    CONF_HISTORY_SIZE,
    CONF_LAST_PERIOD,
    CONF_LUTEAL_PHASE,
    CONF_PERIOD_LENGTH,
    DEFAULTS,
    DOMAIN,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

type MenstrualCycleConfigEntry = ConfigEntry[MenstrualCycleCoordinator]


def today() -> date:
    """Return today's date in the Home Assistant time zone."""
    return dt_util.now().date()


def storage_key(entry_id: str) -> str:
    """Return the storage key for a config entry."""
    return f"{DOMAIN}.{entry_id}"


@dataclass(frozen=True, slots=True)
class CycleData:
    """Logged periods and the prediction computed from them."""

    periods: tuple[Period, ...]
    ovulations: tuple[Ovulation, ...]
    prediction: Prediction | None
    period_length: int


class MenstrualCycleCoordinator(DataUpdateCoordinator[CycleData]):
    """Keeps the logged periods and recomputes the prediction."""

    config_entry: MenstrualCycleConfigEntry

    def __init__(self, hass: HomeAssistant, entry: MenstrualCycleConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=None,
        )
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, storage_key(entry.entry_id)
        )
        self._periods: list[Period] = []
        self._ovulations: list[Ovulation] = []

    def setting(self, key: str) -> int:
        """Return a setting, preferring the options over the initial data."""
        options = {**self.config_entry.data, **self.config_entry.options}
        return int(options.get(key, DEFAULTS[key]))

    async def async_load(self) -> None:
        """Load the logged periods and schedule the daily refresh."""
        stored = await self._store.async_load()
        if stored is None:
            if initial := self.config_entry.data.get(CONF_LAST_PERIOD):
                self._periods = [Period(date.fromisoformat(initial))]
                await self._async_save()
        else:
            self._periods = [
                Period(
                    start=date.fromisoformat(item["start"]),
                    end=date.fromisoformat(item["end"]) if item.get("end") else None,
                )
                for item in stored.get("periods", [])
            ]
            self._ovulations = [
                Ovulation(
                    observed=date.fromisoformat(item["date"]),
                    method=OvulationMethod(item.get("method", OvulationMethod.OTHER)),
                )
                for item in stored.get("ovulations", [])
            ]
        self._periods.sort(key=lambda p: p.start)
        self._ovulations.sort(key=lambda o: o.observed)

        # Phase and countdowns depend on the date, so recompute after midnight.
        self.config_entry.async_on_unload(
            async_track_time_change(
                self.hass, self._async_midnight, hour=0, minute=0, second=5
            )
        )

    async def _async_midnight(self, _now: datetime) -> None:
        await self.async_refresh()

    async def _async_update_data(self) -> CycleData:
        period_length = self.setting(CONF_PERIOD_LENGTH)
        prediction = predict(
            self._periods,
            today(),
            default_cycle_length=self.setting(CONF_CYCLE_LENGTH),
            default_period_length=period_length,
            luteal_phase=self.setting(CONF_LUTEAL_PHASE),
            history_size=self.setting(CONF_HISTORY_SIZE),
            forecast_cycles=self.setting(CONF_FORECAST_CYCLES),
            ovulations=self._ovulations,
        )
        return CycleData(
            periods=tuple(self._periods),
            ovulations=tuple(self._ovulations),
            prediction=prediction,
            period_length=prediction.period_length if prediction else period_length,
        )

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "periods": [
                    {
                        "start": p.start.isoformat(),
                        "end": p.end.isoformat() if p.end else None,
                    }
                    for p in self._periods
                ],
                "ovulations": [
                    {"date": o.observed.isoformat(), "method": o.method.value}
                    for o in self._ovulations
                ],
            }
        )

    async def _async_commit(self) -> None:
        self._periods.sort(key=lambda p: p.start)
        self._ovulations.sort(key=lambda o: o.observed)
        await self._async_save()
        await self.async_refresh()

    def _check_free(self, start: date, end: date | None = None) -> None:
        """Raise if a new period would overlap a logged one."""
        last = end or start
        for period in self._periods:
            if period.start <= last and start <= (period.end or period.start):
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="period_overlaps",
                    translation_placeholders={"date": period.start.isoformat()},
                )

    async def async_log_period_start(self, start: date) -> None:
        """Log the first day of a period."""
        self._check_free(start)
        self._periods.append(Period(start))
        await self._async_commit()

    async def async_log_period_end(self, end: date) -> None:
        """Set the last day of the most recent period starting on or before ``end``."""
        candidates = [p for p in self._periods if p.start <= end]
        if not candidates:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="no_period_to_end"
            )
        period = candidates[-1]
        if (end - period.start).days >= MAX_PERIOD_LENGTH:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="period_too_long",
                translation_placeholders={
                    "date": period.start.isoformat(),
                    "max": str(MAX_PERIOD_LENGTH),
                },
            )
        self._periods[self._periods.index(period)] = replace(period, end=end)
        await self._async_commit()

    async def async_add_period(self, start: date, end: date | None) -> None:
        """Log a whole period, e.g. a past one."""
        if end is not None and not 0 <= (end - start).days < MAX_PERIOD_LENGTH:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="invalid_period",
                translation_placeholders={"max": str(MAX_PERIOD_LENGTH)},
            )
        self._check_free(start, end)
        self._periods.append(Period(start, end))
        await self._async_commit()

    async def async_log_ovulation(self, observed: date, method: OvulationMethod) -> None:
        """Log an ovulation sign, replacing any other one in the same cycle."""
        ovulation = Ovulation(observed, method)
        starts = [p.start for p in self._periods if p.start <= ovulation.estimated]
        if not starts:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="no_period_for_ovulation"
            )
        cycle_start = starts[-1]
        cycle_end = next((p.start for p in self._periods if p.start > cycle_start), None)
        self._ovulations = [
            o
            for o in self._ovulations
            if not (
                cycle_start <= o.estimated and (cycle_end is None or o.estimated < cycle_end)
            )
        ]
        self._ovulations.append(ovulation)
        await self._async_commit()

    async def async_delete_ovulation(self, observed: date) -> None:
        """Delete the ovulation sign logged on ``observed``."""
        for ovulation in self._ovulations:
            if ovulation.observed == observed:
                self._ovulations.remove(ovulation)
                await self._async_commit()
                return
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="ovulation_not_found",
            translation_placeholders={"date": observed.isoformat()},
        )

    async def async_delete_period(self, start: date) -> None:
        """Delete the period starting on ``start``."""
        for period in self._periods:
            if period.start == start:
                self._periods.remove(period)
                await self._async_commit()
                return
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="period_not_found",
            translation_placeholders={"date": start.isoformat()},
        )
