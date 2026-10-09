"""Password hashing, sessions and brute-force protection for the web page.

This module only uses the standard library so it can be tested without
Home Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import secrets

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 256

# scrypt parameters: ~16 MiB of memory and some tens of ms per attempt,
# which makes offline guessing of a leaked hash expensive.
_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}

SESSION_TTL = 12 * 3600
MAX_SESSIONS = 50

FAILURE_WINDOW = 15 * 60
MAX_FAILURES_PER_IP = 5
MAX_FAILURES_TOTAL = 30


def hash_password(password: str, salt_hex: str) -> str:
    """Return the scrypt hash of ``password`` as hex."""
    return hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt_hex), maxmem=64 * 1024 * 1024, **_SCRYPT
    ).hex()


def new_password_hash(password: str) -> tuple[str, str]:
    """Hash a new password with a random salt. Returns (hash, salt)."""
    salt = secrets.token_hex(16)
    return hash_password(password, salt), salt


def check_password(password: str, password_hash: str, salt_hex: str) -> bool:
    """Compare in constant time."""
    return hmac.compare_digest(hash_password(password, salt_hex), password_hash)


@dataclass(slots=True)
class Session:
    """A logged-in browser."""

    entry_id: str
    password_hash: str
    expires: float


class WebGuard:
    """Keeps sessions and failed login attempts in memory.

    Everything is lost on restart: sessions end and counters reset, which is
    acceptable for a page with a single password.
    """

    def __init__(self) -> None:
        """Initialize."""
        self._sessions: dict[str, Session] = {}
        self._failures: dict[str, list[float]] = {}
        self._all_failures: list[float] = []

    def _prune(self, now: float) -> None:
        cutoff = now - FAILURE_WINDOW
        self._all_failures = [t for t in self._all_failures if t > cutoff]
        for ip in list(self._failures):
            times = [t for t in self._failures[ip] if t > cutoff]
            if times:
                self._failures[ip] = times
            else:
                del self._failures[ip]
        for token in [t for t, s in self._sessions.items() if s.expires <= now]:
            del self._sessions[token]

    def retry_after(self, ip: str, now: float) -> int | None:
        """Seconds until ``ip`` may try again, or None if it may try now."""
        self._prune(now)
        times = self._failures.get(ip, [])
        if len(times) >= MAX_FAILURES_PER_IP:
            return int(times[-MAX_FAILURES_PER_IP] + FAILURE_WINDOW - now) + 1
        if len(self._all_failures) >= MAX_FAILURES_TOTAL:
            return int(self._all_failures[-MAX_FAILURES_TOTAL] + FAILURE_WINDOW - now) + 1
        return None

    def record_attempt(self, ip: str, now: float) -> None:
        """Count an attempt as failed before checking the password.

        Counting first means parallel requests can't all pass the lockout
        check while the (slow) password checks are running.
        """
        self._failures.setdefault(ip, []).append(now)
        self._all_failures.append(now)

    def record_success(self, ip: str, attempt_time: float) -> None:
        """Forget the failures of an address after a successful login."""
        self._failures.pop(ip, None)
        if attempt_time in self._all_failures:
            self._all_failures.remove(attempt_time)

    def create_session(self, entry_id: str, password_hash: str, now: float) -> str:
        """Start a session and return its token."""
        self._prune(now)
        if len(self._sessions) >= MAX_SESSIONS:
            oldest = min(self._sessions, key=lambda t: self._sessions[t].expires)
            del self._sessions[oldest]
        token = secrets.token_urlsafe(32)
        self._sessions[token] = Session(entry_id, password_hash, now + SESSION_TTL)
        return token

    def get_session(self, token: str | None, now: float) -> Session | None:
        """Return the session for ``token`` if it is still valid."""
        if not token:
            return None
        self._prune(now)
        return self._sessions.get(token)

    def end_session(self, token: str | None) -> None:
        """Log out."""
        if token:
            self._sessions.pop(token, None)
