"""Constants for the Menstrual Cycle integration."""

from typing import Final

DOMAIN: Final = "menstrual_cycle"

CONF_CYCLE_LENGTH: Final = "cycle_length"
CONF_PERIOD_LENGTH: Final = "period_length"
CONF_LUTEAL_PHASE: Final = "luteal_phase"
CONF_HISTORY_SIZE: Final = "history_size"
CONF_FORECAST_CYCLES: Final = "forecast_cycles"
CONF_LAST_PERIOD: Final = "last_period_start"

DEFAULT_CYCLE_LENGTH: Final = 28
DEFAULT_PERIOD_LENGTH: Final = 5
DEFAULT_LUTEAL_PHASE: Final = 14
DEFAULT_HISTORY_SIZE: Final = 6
DEFAULT_FORECAST_CYCLES: Final = 6

DEFAULTS: Final = {
    CONF_CYCLE_LENGTH: DEFAULT_CYCLE_LENGTH,
    CONF_PERIOD_LENGTH: DEFAULT_PERIOD_LENGTH,
    CONF_LUTEAL_PHASE: DEFAULT_LUTEAL_PHASE,
    CONF_HISTORY_SIZE: DEFAULT_HISTORY_SIZE,
    CONF_FORECAST_CYCLES: DEFAULT_FORECAST_CYCLES,
}

STORAGE_VERSION: Final = 1

ATTR_CONFIG_ENTRY: Final = "config_entry"
ATTR_DATE: Final = "date"
ATTR_START: Final = "start"
ATTR_END: Final = "end"
ATTR_METHOD: Final = "method"

SERVICE_LOG_PERIOD_START: Final = "log_period_start"
SERVICE_LOG_PERIOD_END: Final = "log_period_end"
SERVICE_ADD_PERIOD: Final = "add_period"
SERVICE_DELETE_PERIOD: Final = "delete_period"
SERVICE_LOG_OVULATION: Final = "log_ovulation"
SERVICE_DELETE_OVULATION: Final = "delete_ovulation"

UID_PERIOD_PREFIX: Final = "period-"
UID_OVULATION_PREFIX: Final = "ovulation-"

# Calendar event titles can't use translation files, so they live here.
EVENT_LABELS: Final = {
    "en": {
        "period": "Period",
        "predicted_period": "Expected period",
        "fertile": "Fertile window",
        "ovulation": "Ovulation",
        "logged_ovulation": "Ovulation (logged)",
        "prediction": "Estimate based on the logged cycles, not medical advice.",
    },
    "it": {
        "period": "Ciclo",
        "predicted_period": "Ciclo previsto",
        "fertile": "Finestra fertile",
        "ovulation": "Ovulazione",
        "logged_ovulation": "Ovulazione (registrata)",
        "prediction": "Stima basata sui cicli registrati, non è un parere medico.",
    },
}
