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

SETTINGS = {
    "default_cycle_length": 28,
    "default_period_length": 5,
    "luteal_phase": 14,
    "history_size": 6,
    "forecast_cycles": 3,
}


def predict(periods, today):
    return calculator.predict(periods, today, **SETTINGS)


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
