"""Serve the dashboard card and load it in the frontend.

The card is added with ``add_extra_js_url``, so users don't need to add a
dashboard resource by hand.
"""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

CARD_URL = f"/{DOMAIN}/menstrual-cycle-card.js"
CARD_PATH = Path(__file__).parent / "frontend" / "menstrual-cycle-card.js"


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and add it to every frontend page.

    Called from ``async_setup``, which runs once per Home Assistant process,
    so the static path (which can't be unregistered) is added only once.
    """
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=False)]
    )
    # The file name never changes: the version query string makes browsers
    # and the companion apps fetch the new card after an update.
    integration = await async_get_integration(hass, DOMAIN)
    add_extra_js_url(hass, f"{CARD_URL}?v={integration.version}")
