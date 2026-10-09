"""The Menstrual Cycle integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .card import async_register_card
from .const import DOMAIN, STORAGE_VERSION
from .coordinator import MenstrualCycleConfigEntry, MenstrualCycleCoordinator, storage_key
from .services import async_setup_services
from .web import async_register_web

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.CALENDAR, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration services and the dashboard card."""
    async_setup_services(hass)
    await async_register_card(hass)
    await async_register_web(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MenstrualCycleConfigEntry) -> bool:
    """Set up Menstrual Cycle from a config entry."""
    coordinator = MenstrualCycleCoordinator(hass, entry)
    await coordinator.async_load()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: MenstrualCycleConfigEntry) -> None:
    await entry.runtime_data.async_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: MenstrualCycleConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: MenstrualCycleConfigEntry) -> None:
    """Delete the logged periods when the entry is removed."""
    await Store(hass, STORAGE_VERSION, storage_key(entry.entry_id)).async_remove()
