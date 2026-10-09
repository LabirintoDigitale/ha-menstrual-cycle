# Changelog

All notable changes to **Menstrual Cycle for Home Assistant** are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/) loosely; entries are most-recent-first.

## [Unreleased]

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
