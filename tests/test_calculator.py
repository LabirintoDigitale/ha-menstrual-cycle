"""Tests for the prediction logic (no Home Assistant needed)."""

from datetime import date, timedelta
import importlib.util
from pathlib import Path
import sys

import pytest

# Load calculator.py directly so the integration package (which imports
# Home Assistant) is not imported.
_PATH = Path(__file__).parents[1] / "custom_components" / "menstrual_cycle" / "calculator.py"
_spec = importlib.util.spec_from_file_location("calculator", _PATH)
calculator = importlib.util.module_from_spec(_spec)
sys.modules["calculator"] = calculator
_spec.loader.exec_module(calculator)

Period = calculator.Period
Phase = calculator.Phase
Ovulation = calculator.Ovulation
Method = calculator.OvulationMethod

SETTINGS = {
    "default_cycle_length": 28,
    "default_period_length": 5,
    "luteal_phase": 14,
    "history_size": 6,
    "forecast_cycles": 3,
}


def predict(periods, today, ovulations=()):
    return calculator.predict(periods, today, ovulations=ovulations, **SETTINGS)


def test_no_periods():
    assert predict([], date(2026, 10, 9)) is None
    # Periods in the future are ignored.
    assert predict([Period(date(2026, 11, 1))], date(2026, 10, 9)) is None


def test_single_period_uses_defaults():
    p = predict([Period(date(2026, 10, 1))], date(2026, 10, 9))
    assert p.cycle_length == 28
    assert p.period_length == 5
    assert p.cycles_used == 0
    assert p.next_period_start == date(2026, 10, 29)
    assert p.days_until_next_period == 20
    assert p.next_ovulation == date(2026, 10, 15)
    assert p.next_fertile_start == date(2026, 10, 10)
    assert p.next_fertile_end == date(2026, 10, 16)
    assert p.cycle_day == 9
    assert p.phase is Phase.FOLLICULAR
    assert [c.period_start for c in p.upcoming] == [
        date(2026, 10, 29),
        date(2026, 11, 26),
        date(2026, 12, 24),
    ]


def test_average_of_logged_cycles():
    periods = [
        Period(date(2026, 7, 1), date(2026, 7, 4)),
        Period(date(2026, 7, 31), date(2026, 8, 3)),  # 30 days
        Period(date(2026, 8, 30), date(2026, 9, 2)),  # 30 days
        Period(date(2026, 9, 29)),  # 30 days
    ]
    p = predict(periods, date(2026, 10, 9))
    assert p.cycle_length == 30
    assert p.period_length == 4
    assert p.cycles_used == 3
    assert p.next_period_start == date(2026, 10, 29)
    assert p.next_ovulation == date(2026, 10, 15)


def test_outlier_gap_is_ignored():
    periods = [
        Period(date(2026, 5, 1)),
        Period(date(2026, 5, 29)),  # 28 days
        Period(date(2026, 8, 20)),  # 83 days: a missing entry
        Period(date(2026, 9, 17)),  # 28 days
    ]
    p = predict(periods, date(2026, 9, 20))
    assert p.cycle_length == 28
    assert p.cycles_used == 2


def test_history_size_limits_average():
    start = date(2026, 1, 1)
    starts = [start]
    for length in (40, 40, 26, 26, 26, 26, 26, 26):
        starts.append(starts[-1] + timedelta(days=length))
    p = predict([Period(s) for s in starts], starts[-1])
    assert p.cycle_length == 26


@pytest.mark.parametrize(
    ("today", "phase"),
    [
        (date(2026, 10, 1), Phase.MENSTRUATION),
        (date(2026, 10, 5), Phase.MENSTRUATION),
        (date(2026, 10, 6), Phase.FOLLICULAR),
        (date(2026, 10, 10), Phase.FERTILE),
        (date(2026, 10, 15), Phase.OVULATION),
        (date(2026, 10, 16), Phase.FERTILE),
        (date(2026, 10, 17), Phase.LUTEAL),
        (date(2026, 10, 28), Phase.LUTEAL),
        (date(2026, 10, 29), Phase.LATE),
    ],
)
def test_phases(today, phase):
    assert predict([Period(date(2026, 10, 1))], today).phase is phase


def test_logged_end_shortens_menstruation():
    p = predict([Period(date(2026, 10, 1), date(2026, 10, 3))], date(2026, 10, 4))
    assert p.phase is Phase.FOLLICULAR
    assert not p.in_period


def test_after_fertile_window_points_to_next_cycle():
    p = predict([Period(date(2026, 10, 1))], date(2026, 10, 20))
    assert p.next_ovulation == date(2026, 11, 12)
    assert p.next_fertile_start == date(2026, 11, 7)


def test_late_period():
    p = predict([Period(date(2026, 10, 1))], date(2026, 11, 2))
    assert p.phase is Phase.LATE
    assert p.days_until_next_period == -4
    assert p.cycle_day == 33


def test_ovulation_method_offsets():
    day = date(2026, 10, 14)
    assert Ovulation(day, Method.LH_TEST).estimated == date(2026, 10, 15)
    assert Ovulation(day, Method.TEMPERATURE).estimated == date(2026, 10, 13)
    assert Ovulation(day, Method.SYMPTOMS).estimated == day


def _regular_history():
    """Four 30-day cycles from 2026-06-01, ovulation 12 days before each period."""
    starts = [date(2026, 6, 1) + timedelta(days=30 * i) for i in range(5)]
    periods = [Period(s) for s in starts]
    ovulations = [Ovulation(s - timedelta(days=12)) for s in starts[1:]]
    return starts, periods, ovulations


def test_history_records():
    starts, periods, ovulations = _regular_history()
    p = predict(periods, starts[-1], ovulations)
    assert len(p.history) == 4
    record = p.history[0]
    assert record.length == 30
    assert record.ovulation == date(2026, 6, 19)
    assert record.follicular_length == 18
    assert record.luteal_length == 12


def test_personal_luteal_phase_moves_prediction():
    starts, periods, ovulations = _regular_history()
    p = predict(periods, starts[-1], ovulations)
    # (2 * 14 + 4 * 12) / 6 = 12.67 -> 13
    assert p.luteal_length == 13
    assert p.luteal_samples == 4
    assert p.follicular_length == 18
    # Next period 30 days after the last one, ovulation 13 days before it.
    assert p.next_period_start == starts[-1] + timedelta(days=30)
    assert p.next_ovulation == starts[-1] + timedelta(days=17)
    # Identical cycles: no spread, no extra margin.
    assert p.ovulation_sd == 0.0
    assert p.fertile_margin == 0


def test_logged_ovulation_predicts_next_period():
    start = date(2026, 10, 1)
    p = predict([Period(start)], date(2026, 10, 20), [Ovulation(date(2026, 10, 19))])
    # Ovulation on day 19 + 14-day luteal phase, instead of day 29 from the average.
    assert p.current_cycle.ovulation == date(2026, 10, 19)
    assert p.current_cycle.ovulation_confirmed
    assert p.next_period_start == date(2026, 11, 2)
    assert p.phase is Phase.FERTILE
    assert p.next_ovulation_confirmed


def test_implausible_ovulation_is_ignored_in_history():
    periods = [Period(date(2026, 9, 1)), Period(date(2026, 9, 29))]
    # Two days before the next period: a 2-day luteal phase is not plausible.
    p = predict(periods, date(2026, 10, 1), [Ovulation(date(2026, 9, 27))])
    assert p.history[0].ovulation is None
    assert p.luteal_samples == 0


def test_irregular_cycles_widen_fertile_window():
    start = date(2026, 1, 1)
    starts = [start]
    for length in (26, 32, 27, 33):
        starts.append(starts[-1] + timedelta(days=length))
    p = predict([Period(s) for s in starts], starts[-1])
    assert p.cycle_length == 30  # mean 29.5, rounded half to even
    assert p.ovulation_sd == 3.5
    assert p.fertile_margin == 3
    cycle = p.upcoming[0]
    assert (cycle.ovulation - cycle.fertile_start).days == 8
    assert (cycle.fertile_end - cycle.ovulation).days == 4
