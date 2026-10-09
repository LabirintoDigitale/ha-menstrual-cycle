# Changelog

All notable changes to **Menstrual Cycle for Home Assistant** are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/) loosely; entries are most-recent-first.

## [Unreleased]

## [0.5.0] - 2026-10-09

### Added

- **Password-protected web page** at `/menstrual_cycle/view`, outside the Home Assistant UI: the cycle gauge, next period, ovulation, fertile window and the next three cycles. Enabled, with its own password, in the integration options.
  - Password stored as a salted scrypt hash, never in clear.
  - 5 wrong passwords lock the IP address for 15 minutes, 30 lock all logins; attempts are counted before the password check, so parallel requests can't bypass the limit; each failure is delayed by one second.
  - Failed logins go through Home Assistant's own handling (notification, IP ban when `ip_ban_enabled` is set).
  - Session: random `HttpOnly`, `SameSite=Strict` cookie scoped to the page, 12 hours; changing the password ends all sessions.
  - Strict Content-Security-Policy with a per-response script nonce, `frame-ancestors 'none'`, `no-store`, `noindex`; JSON-only login (no cross-site form posts); warning when opened over plain http.

## [0.4.1] - 2026-10-09

### Changed

- **The calendar is pink** in dashboards and in the Calendar panel (Home Assistant 2026.2+). New calendars get it as their initial colour; existing ones get it once, only if no colour was chosen. It can still be changed in the entity settings.

## [0.4.0] - 2026-10-09

### Added

- **"Ovulation peak (test)" button** and `lh_peak` method for `log_ovulation`: the ovulation test shows the LH peak, ovulation is estimated the same day (it follows the peak by about 16 hours).

### Changed

- **"Positive LH test today" renamed "Ovulation (positive test)"**: LH rising, ovulation estimated the next day, as before.

### Removed

- **"Ovulation today" button** (ovulation without a test). It is removed from the entity registry on update; the `log_ovulation` action still accepts ultrasound, symptoms and other methods.

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
