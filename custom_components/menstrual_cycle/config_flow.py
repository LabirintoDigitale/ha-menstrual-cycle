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
    BooleanSelector,
    DateSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_CYCLE_LENGTH,
    CONF_FORECAST_CYCLES,
    CONF_HISTORY_SIZE,
    CONF_LAST_PERIOD,
    CONF_LUTEAL_PHASE,
    CONF_PERIOD_LENGTH,
    CONF_WEB_ENABLED,
    CONF_WEB_PASSWORD,
    CONF_WEB_PASSWORD_HASH,
    CONF_WEB_PASSWORD_SALT,
    DEFAULTS,
    DOMAIN,
)
from .security import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH, new_password_hash

WEB_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_WEB_ENABLED, default=False): BooleanSelector(),
        vol.Optional(CONF_WEB_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="new-password")
        ),
    }
)


def _days(minimum: int, maximum: int, unit: str | None = "d") -> NumberSelector:
    config = NumberSelectorConfig(
        min=minimum, max=maximum, step=1, mode=NumberSelectorMode.BOX
    )
    if unit is not None:
        config["unit_of_measurement"] = unit
    return NumberSelector(config)


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
        """Manage the settings and the web page."""
        errors: dict[str, str] = {}
        if user_input is not None:
            settings, errors = _clean_settings(user_input)
            web, web_errors = await self._web_options(user_input)
            errors.update(web_errors)
            if not errors:
                return self.async_create_entry(data={**settings, **web})

        current = {**DEFAULTS, **self.config_entry.data, **self.config_entry.options}
        # Never send the password (or its hash) back to the form.
        suggested = {k: v for k, v in (user_input or current).items() if k != CONF_WEB_PASSWORD}
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                SETTINGS_SCHEMA.extend(WEB_SCHEMA.schema), suggested
            ),
            errors=errors,
        )

    async def _web_options(
        self, user_input: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Hash a new password, or keep the current one when left empty."""
        enabled = bool(user_input.get(CONF_WEB_ENABLED))
        password = user_input.get(CONF_WEB_PASSWORD) or ""
        current = self.config_entry.options
        web: dict[str, Any] = {CONF_WEB_ENABLED: enabled}
        if password:
            if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
                return web, {CONF_WEB_PASSWORD: "password_length"}
            password_hash, salt = await self.hass.async_add_executor_job(
                new_password_hash, password
            )
            web.update({CONF_WEB_PASSWORD_HASH: password_hash, CONF_WEB_PASSWORD_SALT: salt})
        elif current.get(CONF_WEB_PASSWORD_HASH):
            web.update(
                {
                    CONF_WEB_PASSWORD_HASH: current[CONF_WEB_PASSWORD_HASH],
                    CONF_WEB_PASSWORD_SALT: current[CONF_WEB_PASSWORD_SALT],
                }
            )
        elif enabled:
            return web, {CONF_WEB_PASSWORD: "password_required"}
        return web, {}
