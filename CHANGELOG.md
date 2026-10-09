# Changelog

All notable changes to **Menstrual Cycle for Home Assistant** are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/) loosely; entries are most-recent-first.

## [Unreleased]

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
