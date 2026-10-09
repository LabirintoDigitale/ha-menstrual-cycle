"""Services for the Menstrual Cycle integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_CONFIG_ENTRY,
    ATTR_DATE,
    ATTR_END,
    ATTR_START,
    DOMAIN,
    SERVICE_ADD_PERIOD,
    SERVICE_DELETE_PERIOD,
    SERVICE_LOG_PERIOD_END,
    SERVICE_LOG_PERIOD_START,
)
from .coordinator import MenstrualCycleConfigEntry, MenstrualCycleCoordinator, today

SCHEMA_OPTIONAL_DATE = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
        vol.Optional(ATTR_DATE): cv.date,
    }
)
SCHEMA_REQUIRED_DATE = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
        vol.Required(ATTR_DATE): cv.date,
    }
)
SCHEMA_ADD_PERIOD = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
        vol.Required(ATTR_START): cv.date,
        vol.Optional(ATTR_END): cv.date,
    }
)


def _get_coordinator(hass: HomeAssistant, call: ServiceCall) -> MenstrualCycleCoordinator:
    """Return the coordinator targeted by the call.

    The config entry may be omitted when only one is set up.
    """
    entries: list[MenstrualCycleConfigEntry] = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    if entry_id := call.data.get(ATTR_CONFIG_ENTRY):
        entries = [entry for entry in entries if entry.entry_id == entry_id]
        if not entries:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="entry_not_found"
            )
    elif len(entries) != 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_required" if entries else "entry_not_found",
        )
    return entries[0].runtime_data


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration services."""

    async def log_period_start(call: ServiceCall) -> None:
        await _get_coordinator(hass, call).async_log_period_start(
            call.data.get(ATTR_DATE) or today()
        )

    async def log_period_end(call: ServiceCall) -> None:
        await _get_coordinator(hass, call).async_log_period_end(
            call.data.get(ATTR_DATE) or today()
        )

    async def add_period(call: ServiceCall) -> None:
        await _get_coordinator(hass, call).async_add_period(
            call.data[ATTR_START], call.data.get(ATTR_END)
        )

    async def delete_period(call: ServiceCall) -> None:
        await _get_coordinator(hass, call).async_delete_period(call.data[ATTR_DATE])

    hass.services.async_register(
        DOMAIN, SERVICE_LOG_PERIOD_START, log_period_start, schema=SCHEMA_OPTIONAL_DATE
    )
    hass.services.async_register(
        DOMAIN, SERVICE_LOG_PERIOD_END, log_period_end, schema=SCHEMA_OPTIONAL_DATE
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_PERIOD, add_period, schema=SCHEMA_ADD_PERIOD
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_PERIOD, delete_period, schema=SCHEMA_REQUIRED_DATE
    )
