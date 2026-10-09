/*
 * Menstrual Cycle card: a gauge with one segment per day of the cycle,
 * period days in red, the fertile window in pink and today marked.
 *
 * Served and loaded by the integration itself (see card.py): no dashboard
 * resource is needed. It reads the attributes of the "Cycle day" sensor.
 */

const CARD_TYPE = "menstrual-cycle-card";
const DOMAIN = "menstrual_cycle";

const COLORS = {
  period: "#e53935",
  fertile: "#f48fb1",
  ovulation: "#c2185b",
  late: "#ffa000",
};

const TRANSLATIONS = {
  en: {
    card_name: "Menstrual Cycle",
    card_description: "Gauge with the days of the cycle, the period and the fertile window.",
    day: "Day",
    of: (n) => `of ${n}`,
    phases: {
      menstruation: "Menstruation",
      follicular: "Follicular",
      fertile: "Fertile",
      ovulation: "Ovulation",
      luteal: "Luteal",
      late: "Late",
    },
    next_in: (n, d) => (n === 0 ? `Next period expected today` : n === 1 ? `Next period tomorrow · ${d}` : `Next period in ${n} days · ${d}`),
    late_by: (n) => (n === 1 ? `Period 1 day late` : `Period ${n} days late`),
    legend: { period: "Period", fertile: "Fertile window", ovulation: "Ovulation", today: "Today" },
    no_period: "Log a period to see the cycle.",
    not_found: (e) => `Entity not found: ${e}`,
    wrong_entity: "Choose the “Cycle day” sensor of Menstrual Cycle.",
    example: "Example",
    editor: { entity: "“Cycle day” sensor", name: "Title", show_legend: "Show legend", show_next: "Show next period" },
  },
  it: {
    card_name: "Ciclo mestruale",
    card_description: "Gauge con i giorni del ciclo, le mestruazioni e la finestra fertile.",
    day: "Giorno",
    of: (n) => `di ${n}`,
    phases: {
      menstruation: "Mestruazioni",
      follicular: "Follicolare",
      fertile: "Fertile",
      ovulation: "Ovulazione",
      luteal: "Luteale",
      late: "In ritardo",
    },
    next_in: (n, d) => (n === 0 ? `Prossimo ciclo previsto oggi` : n === 1 ? `Prossimo ciclo domani · ${d}` : `Prossimo ciclo tra ${n} giorni · ${d}`),
    late_by: (n) => (n === 1 ? `Ciclo in ritardo di 1 giorno` : `Ciclo in ritardo di ${n} giorni`),
    legend: { period: "Mestruazioni", fertile: "Finestra fertile", ovulation: "Ovulazione", today: "Oggi" },
    no_period: "Registra un ciclo per vedere il grafico.",
    not_found: (e) => `Entità non trovata: ${e}`,
    wrong_entity: "Scegli il sensore “Giorno del ciclo” di Menstrual Cycle.",
    example: "Esempio",
    editor: { entity: "Sensore “Giorno del ciclo”", name: "Titolo", show_legend: "Mostra legenda", show_next: "Mostra prossimo ciclo" },
  },
};

function strings(hass) {
  const lang = (hass?.locale?.language || hass?.language || navigator.language || "en").slice(0, 2);
  return TRANSLATIONS[lang] || TRANSLATIONS.en;
}

/** Find the "Cycle day" sensor of the integration, for the card picker. */
function findCycleDaySensor(hass) {
  const entries = Object.values(hass?.entities || {});
  const match = entries.find(
    (e) => e.platform === DOMAIN && e.translation_key === "cycle_day" && e.entity_id.startsWith("sensor.")
  );
  if (match) return match.entity_id;
  // Fallback: any sensor carrying the card attributes.
  return Object.keys(hass?.states || {}).find(
    (id) => id.startsWith("sensor.") && hass.states[id].attributes.fertile_start_day !== undefined
  );
}

function demoData() {
  const next = new Date();
  next.setDate(next.getDate() + 17);
  return {
    demo: true,
    day: 12,
    cycleLength: 28,
    periodLength: 5,
    fertileStart: 10,
    ovulation: 15,
    fertileEnd: 16,
    phase: "fertile",
    nextPeriod: next.toISOString().slice(0, 10),
    daysUntil: 17,
  };
}

const CX = 100;
const CY = 100;
const R = 78;
const START = 135; // degrees, bottom-left; the gauge spans 270°
const SWEEP = 270;

function point(angle, radius = R) {
  const rad = (angle * Math.PI) / 180;
  return [CX + radius * Math.cos(rad), CY + radius * Math.sin(rad)];
}

function arc(a0, a1, radius = R) {
  const [x0, y0] = point(a0, radius);
  const [x1, y1] = point(a1, radius);
  const large = a1 - a0 > 180 ? 1 : 0;
  return `M ${x0.toFixed(2)} ${y0.toFixed(2)} A ${radius} ${radius} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

class MenstrualCycleCard extends HTMLElement {
  static getStubConfig(hass) {
    return { entity: findCycleDaySensor(hass) || "" };
  }

  static getConfigElement() {
    return document.createElement(`${CARD_TYPE}-editor`);
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = { show_legend: true, show_next: true, ...config };
    this._render();
  }

  set hass(hass) {
    const previous = this._hass;
    this._hass = hass;
    const state = this._config?.entity ? hass.states[this._config.entity] : undefined;
    if (!previous || state !== this._state || previous.language !== hass.language) {
      this._state = state;
      this._render();
    }
  }

  getCardSize() {
    return 5;
  }

  getGridOptions() {
    return { columns: 6, min_columns: 4 };
  }

  _data() {
    const entity = this._config.entity;
    if (!entity) return demoData();
    const state = this._hass?.states[entity];
    if (!state) return { message: strings(this._hass).not_found(entity) };
    const a = state.attributes;
    if (a.cycle_length === undefined) {
      const known = state.state === "unknown" || state.state === "unavailable";
      return { message: known ? strings(this._hass).no_period : strings(this._hass).wrong_entity };
    }
    return {
      day: Number(state.state),
      cycleLength: a.cycle_length,
      periodLength: a.period_length,
      fertileStart: a.fertile_start_day,
      ovulation: a.ovulation_day,
      fertileEnd: a.fertile_end_day,
      phase: a.phase,
      nextPeriod: a.next_period,
      daysUntil: a.days_until_next_period,
    };
  }

  _dayColor(d, i) {
    if (i > d.cycleLength) return COLORS.late;
    if (i <= d.periodLength) return COLORS.period;
    if (i === d.ovulation) return COLORS.ovulation;
    if (i >= d.fertileStart && i <= d.fertileEnd) return COLORS.fertile;
    return null;
  }

  _gauge(d, t) {
    const total = Math.max(d.cycleLength, d.day);
    const span = SWEEP / total;
    const gap = Math.min(1.6, span * 0.3);
    const parts = [];

    // Track behind the segments.
    parts.push(`<path d="${arc(START, START + SWEEP)}" class="track"/>`);

    for (let i = 1; i <= total; i++) {
      const a0 = START + (i - 1) * span + gap / 2;
      const a1 = START + i * span - gap / 2;
      const color = this._dayColor(d, i);
      const past = i <= d.day;
      const style = color
        ? `stroke:${color};opacity:${past ? 1 : 0.5}`
        : `stroke:var(--secondary-text-color);opacity:${past ? 0.45 : 0.15}`;
      parts.push(`<path d="${arc(a0, a1)}" class="seg" style="${style}"/>`);
    }

    // Day numbers: 1, every 7 days and the last day.
    const labels = new Set([1, total]);
    for (let i = 7; i < total - 2; i += 7) labels.add(i);
    for (const i of labels) {
      const [x, y] = point(START + (i - 0.5) * span, R + 17);
      parts.push(`<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" class="tick">${i}</text>`);
    }

    // Today.
    const today = Math.min(Math.max(d.day, 1), total);
    const [tx, ty] = point(START + (today - 0.5) * span);
    parts.push(`<circle cx="${tx.toFixed(2)}" cy="${ty.toFixed(2)}" r="8.5" class="today"/>`);

    const phaseColor =
      d.phase === "menstruation" ? COLORS.period
      : d.phase === "ovulation" ? COLORS.ovulation
      : d.phase === "fertile" ? COLORS.fertile
      : d.phase === "late" ? COLORS.late
      : "var(--secondary-text-color)";

    parts.push(`<text x="${CX}" y="74" class="label">${escapeHtml(t.day)}</text>`);
    parts.push(`<text x="${CX}" y="110" class="day">${d.day}</text>`);
    parts.push(`<text x="${CX}" y="128" class="label">${escapeHtml(t.of(d.cycleLength))}</text>`);
    parts.push(`<text x="${CX}" y="152" class="phase" style="fill:${phaseColor}">${escapeHtml(t.phases[d.phase] || d.phase || "")}</text>`);

    return `<svg viewBox="0 0 200 182" role="img" aria-label="${escapeHtml(`${t.day} ${d.day} ${t.of(d.cycleLength)}`)}">${parts.join("")}</svg>`;
  }

  _nextText(d, t) {
    if (d.daysUntil < 0) return t.late_by(-d.daysUntil);
    const locale = this._hass?.locale?.language || this._hass?.language;
    const date = new Date(`${d.nextPeriod}T00:00:00`).toLocaleDateString(locale, { day: "numeric", month: "short" });
    return t.next_in(d.daysUntil, date);
  }

  _render() {
    if (!this._config) return;
    const t = strings(this._hass);
    const d = this._data();
    const title = this._config.name ? `<div class="title">${escapeHtml(this._config.name)}</div>` : "";

    let body;
    if (d.message) {
      body = `<div class="message">${escapeHtml(d.message)}</div>`;
    } else {
      const legend = this._config.show_legend
        ? `<div class="legend">
            <span><i style="background:${COLORS.period}"></i>${escapeHtml(t.legend.period)}</span>
            <span><i style="background:${COLORS.fertile}"></i>${escapeHtml(t.legend.fertile)}</span>
            <span><i style="background:${COLORS.ovulation}"></i>${escapeHtml(t.legend.ovulation)}</span>
            <span><i class="dot"></i>${escapeHtml(t.legend.today)}</span>
          </div>`
        : "";
      const next = this._config.show_next ? `<div class="next">${escapeHtml(this._nextText(d, t))}</div>` : "";
      const demo = d.demo ? `<div class="demo">${escapeHtml(t.example)}</div>` : "";
      body = `${demo}${this._gauge(d, t)}${next}${legend}`;
    }

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 16px; cursor: ${this._config.entity ? "pointer" : "default"}; position: relative; }
        .title { font-size: 1.1em; font-weight: 500; margin-bottom: 4px; color: var(--primary-text-color); }
        svg { display: block; width: 100%; max-width: 280px; margin: 0 auto; }
        .track { fill: none; stroke: var(--divider-color); stroke-width: 18; opacity: 0.35; }
        .seg { fill: none; stroke-width: 14; }
        .tick { font-size: 8px; fill: var(--secondary-text-color); text-anchor: middle; dominant-baseline: middle; }
        .today { fill: var(--primary-text-color); stroke: var(--card-background-color, var(--ha-card-background, #fff)); stroke-width: 3; }
        .label { font-size: 10px; fill: var(--secondary-text-color); text-anchor: middle; }
        .day { font-size: 36px; font-weight: 600; fill: var(--primary-text-color); text-anchor: middle; }
        .phase { font-size: 12px; font-weight: 600; text-anchor: middle; }
        .next { text-align: center; color: var(--primary-text-color); margin-top: 2px; }
        .legend { display: flex; flex-wrap: wrap; justify-content: center; gap: 4px 14px; margin-top: 10px; font-size: 0.85em; color: var(--secondary-text-color); }
        .legend span { display: inline-flex; align-items: center; gap: 6px; }
        .legend i { width: 12px; height: 6px; border-radius: 3px; display: inline-block; }
        .legend i.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--primary-text-color); }
        .message { padding: 24px 8px; text-align: center; color: var(--secondary-text-color); }
        .demo { position: absolute; top: 12px; right: 16px; font-size: 0.75em; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.05em; }
      </style>
      <ha-card>${title}${body}</ha-card>
    `;
    this.shadowRoot.querySelector("ha-card").addEventListener("click", () => this._moreInfo());
  }

  _moreInfo() {
    if (!this._config.entity) return;
    this.dispatchEvent(
      new CustomEvent("hass-more-info", { detail: { entityId: this._config.entity }, bubbles: true, composed: true })
    );
  }
}

class MenstrualCycleCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    const t = strings(this._hass);
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) => t.editor[schema.name] || schema.name;
      this._form.addEventListener("value-changed", (ev) => {
        this.dispatchEvent(
          new CustomEvent("config-changed", { detail: { config: ev.detail.value }, bubbles: true, composed: true })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = { show_legend: true, show_next: true, ...this._config };
    this._form.schema = [
      { name: "entity", required: true, selector: { entity: { filter: { integration: DOMAIN, domain: "sensor" } } } },
      { name: "name", selector: { text: {} } },
      {
        type: "grid",
        name: "",
        schema: [
          { name: "show_next", selector: { boolean: {} } },
          { name: "show_legend", selector: { boolean: {} } },
        ],
      },
    ];
  }
}

if (!customElements.get(CARD_TYPE)) {
  customElements.define(CARD_TYPE, MenstrualCycleCard);
  customElements.define(`${CARD_TYPE}-editor`, MenstrualCycleCardEditor);

  const t = strings(document.querySelector("home-assistant")?.hass);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: CARD_TYPE,
    name: t.card_name,
    description: t.card_description,
    preview: true,
    documentationURL: "https://github.com/LabirintoDigitale/ha-menstrual-cycle",
  });
}
