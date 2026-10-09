"""Cycle prediction logic.

This module only uses the standard library so it can be tested without
Home Assistant.

How the prediction works:

- The cycle length is the mean of the recent logged cycles. Gaps outside
  15-60 days are treated as missing data and ignored.
- The luteal phase (ovulation -> next period) varies much less within a
  woman than the follicular phase (period -> ovulation), so the ovulation is
  predicted backwards from the next expected period: next period minus the
  personal luteal phase. The personal luteal phase is learnt from the cycles
  with a logged ovulation, starting from the configured value and moving
  towards the measured mean as data accumulates.
- Once the ovulation of the current cycle is logged, the next period is
  predicted from it (ovulation + luteal phase), which is more precise than
  the average cycle length.
- The spread of past ovulation days (or of cycle lengths, without logged
  ovulations) widens the predicted fertile window.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from statistics import mean, stdev

# Gaps between two logged periods outside this range are treated as missing
# data (e.g. a forgotten entry) and ignored when averaging.
MIN_CYCLE_LENGTH = 15
MAX_CYCLE_LENGTH = 60
MAX_PERIOD_LENGTH = 15
# Luteal phases outside this range are treated as wrongly logged ovulations.
MIN_LUTEAL_LENGTH = 7
MAX_LUTEAL_LENGTH = 20

# The fertile window spans the 5 days before ovulation plus the day after.
FERTILE_DAYS_BEFORE_OVULATION = 5
FERTILE_DAYS_AFTER_OVULATION = 1

# Weight of the configured luteal phase, in cycles, against the measured ones.
LUTEAL_PRIOR_WEIGHT = 2
# Samples needed before the spread is used to widen the fertile window.
MIN_SAMPLES_FOR_SPREAD = 3
MAX_FERTILE_MARGIN = 3
# Cycles kept in the history exposed for analysis.
HISTORY_LENGTH = 12


class Phase(StrEnum):
    """Phase of the cycle on a given day."""

    MENSTRUATION = "menstruation"
    FOLLICULAR = "follicular"
    FERTILE = "fertile"
    OVULATION = "ovulation"
    LUTEAL = "luteal"
    LATE = "late"


class OvulationMethod(StrEnum):
    """How an ovulation was detected."""

    LH_TEST = "lh_test"
    LH_PEAK = "lh_peak"
    TEMPERATURE = "temperature"
    ULTRASOUND = "ultrasound"
    SYMPTOMS = "symptoms"
    OTHER = "other"


# Days from the logged observation to the estimated ovulation:
# - ovulation follows the start of the LH rise (first positive test) by
#   about 32 hours, and the LH peak by about 16 hours (WHO data);
# - the basal temperature rises the day after ovulation.
OVULATION_OFFSET = {
    OvulationMethod.LH_TEST: 1,
    OvulationMethod.LH_PEAK: 0,
    OvulationMethod.TEMPERATURE: -1,
    OvulationMethod.ULTRASOUND: 0,
    OvulationMethod.SYMPTOMS: 0,
    OvulationMethod.OTHER: 0,
}


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
class Ovulation:
    """A logged ovulation sign: the day it was observed and how."""

    observed: date
    method: OvulationMethod = OvulationMethod.OTHER

    @property
    def estimated(self) -> date:
        """Estimated day of ovulation."""
        return self.observed + timedelta(days=OVULATION_OFFSET[self.method])


@dataclass(frozen=True, slots=True)
class Cycle:
    """A cycle starting on ``period_start``, with its estimated key dates."""

    period_start: date
    period_end: date
    fertile_start: date
    ovulation: date
    fertile_end: date
    next_period_start: date
    ovulation_confirmed: bool = False


@dataclass(frozen=True, slots=True)
class CycleRecord:
    """A completed cycle, for the history."""

    start: date
    length: int
    period_length: int | None
    ovulation: date | None
    follicular_length: int | None
    luteal_length: int | None


@dataclass(frozen=True, slots=True)
class Prediction:
    """Result of a prediction for a given day."""

    today: date
    last_period: Period
    cycle_length: int
    period_length: int
    cycles_used: int
    cycle_length_sd: float | None
    luteal_length: int
    luteal_samples: int
    follicular_length: int | None
    ovulation_sd: float | None
    cycle_day: int
    phase: Phase
    current_cycle: Cycle
    upcoming: tuple[Cycle, ...]
    next_fertile_start: date
    next_ovulation: date
    next_fertile_end: date
    next_ovulation_confirmed: bool
    history: tuple[CycleRecord, ...]

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

    @property
    def fertile_margin(self) -> int:
        """Days added on each side of the predicted fertile window."""
        return _margin(self.ovulation_sd)


def build_cycle(
    start: date,
    cycle_length: int,
    period_length: int,
    luteal_phase: int,
    *,
    ovulation: date | None = None,
    margin: int = 0,
) -> Cycle:
    """Estimate the key dates of a cycle starting on ``start``.

    With a known ``ovulation`` the next period follows it by the luteal
    phase; otherwise the ovulation is placed ``luteal_phase`` days before
    the next period.
    """
    confirmed = ovulation is not None
    if ovulation is not None:
        next_start = ovulation + timedelta(days=luteal_phase)
        margin = 0
    else:
        next_start = start + timedelta(days=cycle_length)
        ovulation = start + timedelta(days=max(cycle_length - luteal_phase, 1))
    return Cycle(
        period_start=start,
        period_end=start + timedelta(days=period_length - 1),
        fertile_start=max(
            ovulation - timedelta(days=FERTILE_DAYS_BEFORE_OVULATION + margin), start
        ),
        ovulation=ovulation,
        fertile_end=ovulation + timedelta(days=FERTILE_DAYS_AFTER_OVULATION + margin),
        next_period_start=next_start,
        ovulation_confirmed=confirmed,
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
    ovulations: Iterable[Ovulation] = (),
) -> Prediction | None:
    """Predict the upcoming cycles from the logged periods and ovulations.

    Returns None when no period has been logged up to ``today``.
    """
    past = sorted((p for p in periods if p.start <= today), key=lambda p: p.start)
    if not past:
        return None
    last = past[-1]
    estimated = sorted(o.estimated for o in ovulations if o.estimated <= today)

    history = _history(past, estimated)
    recent = history[-history_size:]

    cycle_lengths = [r.length for r in recent]
    cycle_length = round(mean(cycle_lengths)) if cycle_lengths else default_cycle_length
    cycle_length_sd = _sd(cycle_lengths)

    period_lengths = [
        (p.end - p.start).days + 1
        for p in past
        if p.end is not None and p.end >= p.start
    ][-history_size:]
    period_length = (
        round(mean(period_lengths)) if period_lengths else default_period_length
    )

    luteals = [r.luteal_length for r in recent if r.luteal_length is not None]
    luteal_length = round(
        (LUTEAL_PRIOR_WEIGHT * luteal_phase + sum(luteals))
        / (LUTEAL_PRIOR_WEIGHT + len(luteals))
    )
    follicular = [r.follicular_length for r in recent if r.follicular_length is not None]

    # Without enough logged ovulations, the spread of the cycle lengths is
    # the best proxy for the spread of the ovulation day.
    ovulation_sd = (
        _sd(follicular)
        if len(follicular) >= MIN_SAMPLES_FOR_SPREAD
        else (cycle_length_sd if len(cycle_lengths) >= MIN_SAMPLES_FOR_SPREAD else None)
    )
    margin = _margin(ovulation_sd)

    current_ovulation = next(
        (
            day
            for day in reversed(estimated)
            if last.start < day < last.start + timedelta(days=MAX_CYCLE_LENGTH)
        ),
        None,
    )
    current = build_cycle(
        last.start,
        cycle_length,
        period_length,
        luteal_length,
        ovulation=current_ovulation,
        margin=margin,
    )

    upcoming = tuple(
        build_cycle(
            current.next_period_start + timedelta(days=i * cycle_length),
            cycle_length,
            period_length,
            luteal_length,
            margin=margin,
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
        cycle_length_sd=cycle_length_sd,
        luteal_length=luteal_length,
        luteal_samples=len(luteals),
        follicular_length=round(mean(follicular)) if follicular else None,
        ovulation_sd=ovulation_sd,
        cycle_day=(today - last.start).days + 1,
        phase=_phase(today, last, current, period_length),
        current_cycle=current,
        upcoming=upcoming,
        next_fertile_start=window.fertile_start,
        next_ovulation=window.ovulation,
        next_fertile_end=window.fertile_end,
        next_ovulation_confirmed=window.ovulation_confirmed,
        history=tuple(history[-HISTORY_LENGTH:]),
    )


def _history(past: list[Period], ovulations: list[date]) -> list[CycleRecord]:
    """Describe each completed cycle with a plausible length."""
    records = []
    for a, b in zip(past, past[1:]):
        length = (b.start - a.start).days
        if not MIN_CYCLE_LENGTH <= length <= MAX_CYCLE_LENGTH:
            continue
        ovulation = next((d for d in ovulations if a.start < d < b.start), None)
        luteal = (b.start - ovulation).days if ovulation else None
        if luteal is not None and not MIN_LUTEAL_LENGTH <= luteal <= MAX_LUTEAL_LENGTH:
            ovulation = luteal = None
        records.append(
            CycleRecord(
                start=a.start,
                length=length,
                period_length=(a.end - a.start).days + 1 if a.end else None,
                ovulation=ovulation,
                follicular_length=(ovulation - a.start).days if ovulation else None,
                luteal_length=luteal,
            )
        )
    return records


def _sd(values: list[int]) -> float | None:
    return round(stdev(values), 1) if len(values) >= 2 else None


def _margin(sd: float | None) -> int:
    return min(round(sd), MAX_FERTILE_MARGIN) if sd else 0


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
