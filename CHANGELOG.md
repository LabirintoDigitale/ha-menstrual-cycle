# Changelog

All notable changes to **Menstrual Cycle for Home Assistant** are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/) loosely; entries are most-recent-first.

## [Unreleased]

## [0.3.0] - 2026-10-09

### Added

- **Ovulation logging.** Buttons *Positive LH test today* and *Ovulation today*, actions `log_ovulation` (date and method: LH test, basal temperature rise, ultrasound, symptoms, other) and `delete_ovulation`. The method sets the estimated ovulation day (LH test +1 day, temperature rise −1 day). One ovulation per cycle; logged ovulations appear in the calendar and can be deleted there.
- **Personal luteal phase.** Learnt from the cycles with a logged ovulation, shrunk towards the configured value while there are few of them. The ovulation is predicted as next period − personal luteal phase; once the current cycle's ovulation is logged, the next period is predicted from it.
- **Variability-aware fertile window.** Widened by 1–3 days per side according to the standard deviation of the ovulation day (or of the cycle length, until 3 ovulations are logged).
- **Statistics sensors** (with long-term statistics): luteal and follicular phase length, cycle length variability, ovulation day variability. *Average cycle length* lists the last 12 cycles in its `cycles` attribute; *Ovulation* reports whether it is confirmed and its variability.

## [0.2.1] - 2026-10-09

### Fixed

- **"Configuration error" instead of the cycle card** when another card (e.g. advanced-camera-card) loads a scoped custom element registry polyfill. The polyfill replaces `window.customElements`, dropping the cards defined before it. The card now defines itself in the current registry and checks again every second, so it is found whichever loads first.

## [0.2.0] - 2026-10-09

### Added

- **Cycle card for the dashboard** (`custom:menstrual-cycle-card`). A 270° gauge with one segment per day of the cycle: period days in red, the fertile window in pink, ovulation in dark pink, days past the expected length in amber, and a dot on today. The centre shows the cycle day and the phase, below it the next expected period. It is served and loaded by the integration (no dashboard resource to add), appears in the card picker with a preview and has a visual editor.
- **Attributes on the "Cycle day" sensor** used by the card: `cycle_length`, `period_length`, `fertile_start_day`, `ovulation_day`, `fertile_end_day`, `phase`, `next_period`, `days_until_next_period`.

## [0.1.2] - 2026-10-09

### Added

- **Integration icon** (`brand/icon.png`), shown in Home Assistant and HACS.
- **Versioned releases**: HACS now shows the installed version and offers updates.

## [0.1.1] - 2026-10-09

### Fixed

- **"Invalid handler specified" when adding the integration.** The settings without a unit passed an empty `unit_of_measurement`, which recent Home Assistant versions reject, so `config_flow.py` failed to load.

## [0.1.0] - 2026-10-09

### Added

- First version: calendar with logged periods, expected periods, fertile windows and ovulation; sensors, binary sensors, buttons and actions to log periods; Italian and English translations.
