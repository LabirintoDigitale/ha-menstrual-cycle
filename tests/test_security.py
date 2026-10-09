"""Tests for the web page security helpers (no Home Assistant needed)."""

import importlib.util
from pathlib import Path
import sys

_PATH = Path(__file__).parents[1] / "custom_components" / "menstrual_cycle" / "security.py"
_spec = importlib.util.spec_from_file_location("security", _PATH)
security = importlib.util.module_from_spec(_spec)
sys.modules["security"] = security
_spec.loader.exec_module(security)


def test_password_hash_roundtrip():
    password_hash, salt = security.new_password_hash("correct horse")
    assert password_hash != "correct horse"
    assert security.check_password("correct horse", password_hash, salt)
    assert not security.check_password("wrong horse", password_hash, salt)


def test_same_password_different_salt():
    a = security.new_password_hash("correct horse")
    b = security.new_password_hash("correct horse")
    assert a[0] != b[0]
    assert a[1] != b[1]


def test_lockout_per_ip():
    guard = security.WebGuard()
    for _ in range(security.MAX_FAILURES_PER_IP - 1):
        guard.record_attempt("1.2.3.4", 100.0)
    assert guard.retry_after("1.2.3.4", 100.0) is None
    guard.record_attempt("1.2.3.4", 100.0)
    wait = guard.retry_after("1.2.3.4", 100.0)
    assert wait == security.FAILURE_WINDOW + 1
    # Another address is not affected.
    assert guard.retry_after("5.6.7.8", 100.0) is None
    # The lock expires with the window.
    assert guard.retry_after("1.2.3.4", 100.0 + security.FAILURE_WINDOW + 1) is None


def test_global_lockout():
    guard = security.WebGuard()
    for i in range(security.MAX_FAILURES_TOTAL):
        guard.record_attempt(f"10.0.0.{i}", 100.0)
    assert guard.retry_after("192.168.1.50", 100.0) is not None


def test_success_clears_failures():
    guard = security.WebGuard()
    for _ in range(security.MAX_FAILURES_PER_IP - 1):
        guard.record_attempt("1.2.3.4", 100.0)
    guard.record_attempt("1.2.3.4", 101.0)
    guard.record_success("1.2.3.4", 101.0)
    assert guard.retry_after("1.2.3.4", 101.0) is None


def test_successful_logins_do_not_count_globally():
    guard = security.WebGuard()
    for i in range(security.MAX_FAILURES_TOTAL + 5):
        guard.record_attempt(f"10.0.0.{i}", float(i))
        guard.record_success(f"10.0.0.{i}", float(i))
    assert guard.retry_after("192.168.1.50", 50.0) is None


def test_sessions_expire_and_end():
    guard = security.WebGuard()
    token = guard.create_session("entry", "hash", 100.0)
    assert guard.get_session(token, 100.0).entry_id == "entry"
    assert guard.get_session("not-a-token", 100.0) is None
    assert guard.get_session(None, 100.0) is None
    assert guard.get_session(token, 100.0 + security.SESSION_TTL) is None
    token = guard.create_session("entry", "hash", 200.0)
    guard.end_session(token)
    assert guard.get_session(token, 200.0) is None


def test_session_cap_drops_oldest():
    guard = security.WebGuard()
    first = guard.create_session("entry", "hash", 0.0)
    for i in range(security.MAX_SESSIONS):
        guard.create_session("entry", "hash", float(i + 1))
    assert guard.get_session(first, 1.0) is None
