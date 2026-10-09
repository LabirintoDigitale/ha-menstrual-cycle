"""Password-protected web page showing the cycle, outside the Home Assistant UI.

The page is served at /menstrual_cycle/view. It doesn't use Home Assistant
logins: each config entry with the page enabled has its own password, and
the password entered selects the entry. See security.py for hashing,
sessions and brute-force limits.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from pathlib import Path
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.components.http.ban import process_success_login, process_wrong_login
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .calculator import card_attributes
from .const import (
    CONF_WEB_ENABLED,
    CONF_WEB_PASSWORD_HASH,
    CONF_WEB_PASSWORD_SALT,
    DOMAIN,
)
from .coordinator import MenstrualCycleConfigEntry
from .security import MAX_PASSWORD_LENGTH, SESSION_TTL, WebGuard, check_password

_LOGGER = logging.getLogger(__name__)

PAGE_URL = f"/{DOMAIN}/view"
COOKIE_NAME = "menstrual_cycle_session"
PAGE_TEMPLATE = Path(__file__).parent / "frontend" / "view.html"
# Wrong passwords are answered slowly, on top of the per-address lockout.
FAILURE_DELAY = 1.0


def _security_headers(nonce: str | None = None) -> dict[str, str]:
    script_src = f"'self' 'nonce-{nonce}'" if nonce else "'none'"
    return {
        "Content-Security-Policy": (
            "default-src 'none'; "
            f"script-src {script_src}; "
            # The card sets inline styles on its SVG; no scripts are allowed inline
            # except the page's own nonce'd script.
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        ),
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-Robots-Tag": "noindex, nofollow",
    }


def _web_entries(hass: HomeAssistant) -> list[MenstrualCycleConfigEntry]:
    """Loaded entries with the page enabled and a password set."""
    return [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
        and entry.options.get(CONF_WEB_ENABLED)
        and entry.options.get(CONF_WEB_PASSWORD_HASH)
    ]


async def async_register_web(hass: HomeAssistant) -> None:
    """Register the page and its API. Called once per Home Assistant process."""
    template = await hass.async_add_executor_job(PAGE_TEMPLATE.read_text, "utf-8")
    guard = WebGuard()
    hass.http.register_view(CyclePageView(hass, template))
    hass.http.register_view(CycleLoginView(hass, guard))
    hass.http.register_view(CycleLogoutView(guard))
    hass.http.register_view(CycleDataView(hass, guard))


class CyclePageView(HomeAssistantView):
    """The page itself. It contains no data: it loads it from the API."""

    url = PAGE_URL
    name = f"{DOMAIN}:view"
    requires_auth = False

    def __init__(self, hass: HomeAssistant, template: str) -> None:
        """Initialize."""
        self._hass = hass
        self._template = template

    async def get(self, request: web.Request) -> web.Response:
        """Serve the page with a fresh script nonce."""
        if not _web_entries(self._hass):
            return web.Response(status=404, headers=_security_headers())
        nonce = secrets.token_urlsafe(16)
        return web.Response(
            text=self._template.replace("{{NONCE}}", nonce),
            content_type="text/html",
            headers=_security_headers(nonce),
        )


class CycleLoginView(HomeAssistantView):
    """Check the password and start a session."""

    url = f"{PAGE_URL}/api/login"
    name = f"{DOMAIN}:view:login"
    requires_auth = False

    def __init__(self, hass: HomeAssistant, guard: WebGuard) -> None:
        """Initialize."""
        self._hass = hass
        self._guard = guard

    async def post(self, request: web.Request) -> web.Response:
        """Log in."""
        headers = _security_headers()
        # Requiring JSON means a cross-site form can't post here without a
        # CORS preflight, which Home Assistant doesn't allow for this path.
        if request.content_type != "application/json":
            return self.json({"error": "unsupported"}, 415, headers)

        ip = request.remote or "unknown"
        now = time.monotonic()
        if (wait := self._guard.retry_after(ip, now)) is not None:
            _LOGGER.warning("Cycle page: login from %s refused, locked for %s s", ip, wait)
            return self.json(
                {"error": "locked", "retry_after": wait},
                429,
                {**headers, "Retry-After": str(wait)},
            )

        try:
            body = await request.json()
        except ValueError:
            return self.json({"error": "invalid"}, 400, headers)
        password = body.get("password") if isinstance(body, dict) else None
        if not isinstance(password, str) or not 0 < len(password) <= MAX_PASSWORD_LENGTH:
            return self.json({"error": "invalid"}, 400, headers)

        self._guard.record_attempt(ip, now)
        for entry in _web_entries(self._hass):
            password_hash = entry.options[CONF_WEB_PASSWORD_HASH]
            if await self._hass.async_add_executor_job(
                check_password, password, password_hash, entry.options[CONF_WEB_PASSWORD_SALT]
            ):
                self._guard.record_success(ip, now)
                token = self._guard.create_session(entry.entry_id, password_hash, now)
                process_success_login(request)
                response = self.json({"ok": True}, 200, headers)
                response.set_cookie(
                    COOKIE_NAME,
                    token,
                    max_age=SESSION_TTL,
                    path=PAGE_URL,
                    httponly=True,
                    samesite="Strict",
                    secure=request.secure,
                )
                return response

        _LOGGER.warning("Cycle page: wrong password from %s", ip)
        # Home Assistant's own failed-login handling: notification, and an IP
        # ban if ip_ban_enabled is configured.
        await process_wrong_login(request)
        await asyncio.sleep(FAILURE_DELAY)
        return self.json({"error": "wrong_password"}, 401, headers)


class CycleLogoutView(HomeAssistantView):
    """End the session."""

    url = f"{PAGE_URL}/api/logout"
    name = f"{DOMAIN}:view:logout"
    requires_auth = False

    def __init__(self, guard: WebGuard) -> None:
        """Initialize."""
        self._guard = guard

    async def post(self, request: web.Request) -> web.Response:
        """Log out."""
        self._guard.end_session(request.cookies.get(COOKIE_NAME))
        response = self.json({"ok": True}, 200, _security_headers())
        response.del_cookie(COOKIE_NAME, path=PAGE_URL)
        return response


class CycleDataView(HomeAssistantView):
    """The cycle data, for a logged-in session."""

    url = f"{PAGE_URL}/api/data"
    name = f"{DOMAIN}:view:data"
    requires_auth = False

    def __init__(self, hass: HomeAssistant, guard: WebGuard) -> None:
        """Initialize."""
        self._hass = hass
        self._guard = guard

    async def get(self, request: web.Request) -> web.Response:
        """Return the data of the session's cycle."""
        headers = _security_headers()
        session = self._guard.get_session(request.cookies.get(COOKIE_NAME), time.monotonic())
        entry = next(
            (
                e
                for e in _web_entries(self._hass)
                if session is not None
                and e.entry_id == session.entry_id
                # A new password ends the sessions opened with the old one.
                and e.options[CONF_WEB_PASSWORD_HASH] == session.password_hash
            ),
            None,
        )
        if entry is None:
            return self.json({"error": "unauthorized"}, 401, headers)
        return self.json(self._payload(entry), 200, headers)

    def _payload(self, entry: MenstrualCycleConfigEntry) -> dict[str, Any]:
        prediction = entry.runtime_data.data.prediction
        payload: dict[str, Any] = {
            "title": entry.title,
            "language": self._hass.config.language,
            "cycle": None,
        }
        if prediction is None:
            return payload
        payload.update(
            cycle={"state": prediction.cycle_day, "attributes": card_attributes(prediction)},
            phase=prediction.phase.value,
            next_period=prediction.next_period_start.isoformat(),
            days_until_next_period=prediction.days_until_next_period,
            ovulation=prediction.next_ovulation.isoformat(),
            ovulation_confirmed=prediction.next_ovulation_confirmed,
            fertile_start=prediction.next_fertile_start.isoformat(),
            fertile_end=prediction.next_fertile_end.isoformat(),
            cycle_length=prediction.cycle_length,
            upcoming=[
                {
                    "period_start": cycle.period_start.isoformat(),
                    "fertile_start": cycle.fertile_start.isoformat(),
                    "ovulation": cycle.ovulation.isoformat(),
                    "fertile_end": cycle.fertile_end.isoformat(),
                }
                for cycle in prediction.upcoming[:3]
            ],
        )
        return payload
