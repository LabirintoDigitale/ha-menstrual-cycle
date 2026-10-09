"""Config flow for the Menstrual Cycle integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    DateSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import (
    CONF_CYCLE_LENGTH,
    CONF_FORECAST_CYCLES,
    CONF_HISTORY_SIZE,
    CONF_LAST_PERIOD,
    CONF_LUTEAL_PHASE,
    CONF_PERIOD_LENGTH,
    DEFAULTS,
    DOMAIN,
)


def _days(minimum: int, maximum: int, unit: str | None = "d") -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=1,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement=unit,
        )
    )


SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CYCLE_LENGTH): _days(15, 60),
        vol.Required(CONF_PERIOD_LENGTH): _days(1, 15),
        vol.Required(CONF_LUTEAL_PHASE): _days(8, 20),
        vol.Required(CONF_HISTORY_SIZE): _days(1, 24, None),
        vol.Required(CONF_FORECAST_CYCLES): _days(1, 12, None),
    }
)


def _clean_settings(user_input: dict[str, Any]) -> tuple[dict[str, int], dict[str, str]]:
    """Convert the numbers to int and validate them."""
    settings = {key: int(user_input[key]) for key in DEFAULTS}
    errors: dict[str, str] = {}
    if settings[CONF_LUTEAL_PHASE] >= settings[CONF_CYCLE_LENGTH]:
        errors[CONF_LUTEAL_PHASE] = "luteal_too_long"
    return settings, errors


class MenstrualCycleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Menstrual Cycle."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a name, the last period and the cycle settings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            settings, errors = _clean_settings(user_input)
            if not errors:
                data: dict[str, Any] = dict(settings)
                if last_period := user_input.get(CONF_LAST_PERIOD):
                    data[CONF_LAST_PERIOD] = last_period
                return self.async_create_entry(title=user_input[CONF_NAME], data=data)

        default_name = (
            "Ciclo mestruale" if self.hass.config.language.startswith("it") else "Menstrual cycle"
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): TextSelector(),
                vol.Optional(CONF_LAST_PERIOD): DateSelector(),
            }
        ).extend(SETTINGS_SCHEMA.schema)
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or {CONF_NAME: default_name, **DEFAULTS}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return MenstrualCycleOptionsFlow()


class MenstrualCycleOptionsFlow(OptionsFlow):
    """Change the cycle settings."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the settings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            settings, errors = _clean_settings(user_input)
            if not errors:
                return self.async_create_entry(data=settings)

        current = {**DEFAULTS, **self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                SETTINGS_SCHEMA, user_input or current
            ),
            errors=errors,
        )
