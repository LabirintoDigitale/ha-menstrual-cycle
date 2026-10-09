"""Cycle prediction logic.

This module only uses the standard library so it can be tested without
Home Assistant.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from statistics import mean

# Gaps between two logged periods outside this range are treated as missing
# data (e.g. a forgotten entry) and ignored when averaging.
MIN_CYCLE_LENGTH = 15
MAX_CYCLE_LENGTH = 60
MAX_PERIOD_LENGTH = 15

# The fertile window spans the 5 days before ovulation plus the day after.
FERTILE_DAYS_BEFORE_OVULATION = 5
FERTILE_DAYS_AFTER_OVULATION = 1


class Phase(StrEnum):
    """Phase of the cycle on a given day."""

    MENSTRUATION = "menstruation"
    FOLLICULAR = "follicular"
    FERTILE = "fertile"
    OVULATION = "ovulation"
    LUTEAL = "luteal"
    LATE = "late"


@dataclass(frozen=True, slots=True)
class Period:
    """A logged period. ``end`` is inclusive and may be unknown."""

    start: date
    end: date | None = None

    def last_day(self, default_length: int) -> date:
        """Return the last day, estimating it when the end is unknown."""
        if self.end is not None:
            return self.end
        return self.start + timedelta(days=default_length - 1)


@dataclass(frozen=True, slots=True)
class Cycle:
    """A cycle starting on ``period_start``, with its estimated key dates."""

    period_start: date
    period_end: date
    fertile_start: date
    ovulation: date
    fertile_end: date
    next_period_start: date


@dataclass(frozen=True, slots=True)
class Prediction:
    """Result of a prediction for a given day."""

    today: date
    last_period: Period
    cycle_length: int
    period_length: int
    cycles_used: int
    cycle_day: int
    phase: Phase
    current_cycle: Cycle
    upcoming: tuple[Cycle, ...]
    next_fertile_start: date
    next_ovulation: date
    next_fertile_end: date

    @property
    def next_period_start(self) -> date:
        """First day of the next expected period."""
        return self.upcoming[0].period_start

    @property
    def days_until_next_period(self) -> int:
        """Days until the next period; negative when it is late."""
        return (self.next_period_start - self.today).days

    @property
    def in_period(self) -> bool:
        """Whether today falls within the last logged period."""
        return self.phase is Phase.MENSTRUATION

    @property
    def in_fertile_window(self) -> bool:
        """Whether today falls within the fertile window."""
        return self.phase in (Phase.FERTILE, Phase.OVULATION)


def build_cycle(
    start: date, cycle_length: int, period_length: int, luteal_phase: int
) -> Cycle:
    """Estimate the key dates of a cycle starting on ``start``."""
    ovulation = start + timedelta(days=max(cycle_length - luteal_phase, 1))
    return Cycle(
        period_start=start,
        period_end=start + timedelta(days=period_length - 1),
        fertile_start=max(
            ovulation - timedelta(days=FERTILE_DAYS_BEFORE_OVULATION), start
        ),
        ovulation=ovulation,
        fertile_end=ovulation + timedelta(days=FERTILE_DAYS_AFTER_OVULATION),
        next_period_start=start + timedelta(days=cycle_length),
    )


def predict(
    periods: Iterable[Period],
    today: date,
    *,
    default_cycle_length: int,
    default_period_length: int,
    luteal_phase: int,
    history_size: int,
    forecast_cycles: int,
) -> Prediction | None:
    """Predict the upcoming cycles from the logged periods.

    Returns None when no period has been logged up to ``today``.
    """
    past = sorted((p for p in periods if p.start <= today), key=lambda p: p.start)
    if not past:
        return None
    last = past[-1]

    cycle_lengths = [
        length
        for a, b in zip(past, past[1:])
        if MIN_CYCLE_LENGTH <= (length := (b.start - a.start).days) <= MAX_CYCLE_LENGTH
    ][-history_size:]
    cycle_length = (
        round(mean(cycle_lengths)) if cycle_lengths else default_cycle_length
    )

    period_lengths = [
        (p.end - p.start).days + 1
        for p in past
        if p.end is not None and p.end >= p.start
    ][-history_size:]
    period_length = (
        round(mean(period_lengths)) if period_lengths else default_period_length
    )

    current = build_cycle(last.start, cycle_length, period_length, luteal_phase)
    upcoming = tuple(
        build_cycle(
            current.next_period_start + timedelta(days=i * cycle_length),
            cycle_length,
            period_length,
            luteal_phase,
        )
        for i in range(max(forecast_cycles, 1))
    )
    # Once this cycle's fertile window is over, point to the next one.
    window = current if today <= current.fertile_end else upcoming[0]

    return Prediction(
        today=today,
        last_period=last,
        cycle_length=cycle_length,
        period_length=period_length,
        cycles_used=len(cycle_lengths),
        cycle_day=(today - last.start).days + 1,
        phase=_phase(today, last, current, period_length),
        current_cycle=current,
        upcoming=upcoming,
        next_fertile_start=window.fertile_start,
        next_ovulation=window.ovulation,
        next_fertile_end=window.fertile_end,
    )


def _phase(today: date, last: Period, current: Cycle, period_length: int) -> Phase:
    if today <= last.last_day(period_length):
        return Phase.MENSTRUATION
    if today == current.ovulation:
        return Phase.OVULATION
    if current.fertile_start <= today <= current.fertile_end:
        return Phase.FERTILE
    if today >= current.next_period_start:
        return Phase.LATE
    if today < current.fertile_start:
        return Phase.FOLLICULAR
    return Phase.LUTEAL
