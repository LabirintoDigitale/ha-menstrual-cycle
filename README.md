# Menstrual Cycle per Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/LabirintoDigitale/ha-menstrual-cycle/actions/workflows/validate.yml/badge.svg)](https://github.com/LabirintoDigitale/ha-menstrual-cycle/actions/workflows/validate.yml)

Integrazione personalizzata che tiene un **calendario del ciclo mestruale** in Home Assistant: registri quando arriva il ciclo e lei prevede il prossimo, l'ovulazione e la finestra fertile.

*English below.*

> **Attenzione:** le previsioni sono stime statistiche basate sui cicli registrati. Non sono un parere medico e **non vanno usate come metodo contraccettivo**.

## Cosa offre

- **Card per la dashboard** con un gauge dei giorni del ciclo: mestruazioni in rosso, finestra fertile in rosa, ovulazione in rosa scuro e un pallino sul giorno di oggi. È già inclusa nell'integrazione: non serve aggiungere risorse JavaScript.
- **Calendario** con i cicli registrati, i cicli previsti, le finestre fertili e i giorni di ovulazione. Puoi aggiungere o eliminare un ciclo direttamente dalla scheda calendario.
- **Sensori**: prossimo ciclo, giorni al prossimo ciclo, ovulazione, inizio e fine della finestra fertile, fase (mestruazioni, follicolare, fertile, ovulazione, luteale, in ritardo), giorno del ciclo, ultimo ciclo, durata media di ciclo e mestruazioni.
- **Sensori binari**: *Mestruazioni* e *Finestra fertile*, comodi per le automazioni.
- **Pulsanti**: *Ciclo iniziato oggi* e *Ciclo finito oggi*.
- **Azioni**: `menstrual_cycle.log_period_start`, `log_period_end`, `add_period`, `delete_period`.
- Interfaccia in italiano e inglese. I dati restano solo nel tuo Home Assistant.

## Come calcola le previsioni

- **Durata del ciclo**: media degli ultimi N cicli registrati (6 di default). Gli intervalli fuori da 15–60 giorni vengono ignorati perché probabilmente manca una registrazione. Finché non ci sono almeno due cicli si usa la durata impostata.
- **Prossimo ciclo**: inizio dell'ultimo ciclo + durata media.
- **Ovulazione**: prossimo ciclo − fase luteale (14 giorni di default).
- **Finestra fertile**: dai 5 giorni prima dell'ovulazione al giorno dopo.

## Installazione

### HACS

1. HACS → menu ⋮ → **Repository personalizzati**.
2. Aggiungi `https://github.com/LabirintoDigitale/ha-menstrual-cycle` con tipo **Integrazione**.
3. Installa **Menstrual Cycle** e riavvia Home Assistant.

### Manuale

Copia la cartella `custom_components/menstrual_cycle` nella cartella `config/custom_components` di Home Assistant e riavvia.

## Configurazione

**Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Menstrual Cycle.** Puoi indicare subito il primo giorno dell'ultimo ciclo; le durate abituali si possono cambiare in seguito da **Configura**.

Per inserire cicli passati usa la scheda calendario oppure l'azione `menstrual_cycle.add_period`:

```yaml
action: menstrual_cycle.add_period
data:
  start: "2026-08-30"
  end: "2026-09-03"
```

## Card del ciclo

Modifica la dashboard → **Aggiungi card** → cerca **Ciclo mestruale** (o *Menstrual Cycle*): compare con l'anteprima e si configura dall'editor visuale. In YAML:

```yaml
type: custom:menstrual-cycle-card
entity: sensor.ciclo_mestruale_giorno_del_ciclo
name: Ciclo            # facoltativo
show_next: true        # riga "Prossimo ciclo tra N giorni"
show_legend: true      # legenda dei colori
```

La card legge gli attributi del sensore *Giorno del ciclo*. Toccandola si apre il dettaglio del sensore.

## Esempi

Scheda per la dashboard:

```yaml
type: vertical-stack
cards:
  - type: calendar
    entities:
      - calendar.ciclo_mestruale
    initial_view: dayGridMonth
  - type: entities
    entities:
      - sensor.ciclo_mestruale_fase
      - sensor.ciclo_mestruale_prossimo_ciclo
      - sensor.ciclo_mestruale_giorni_al_prossimo_ciclo
      - sensor.ciclo_mestruale_ovulazione
      - button.ciclo_mestruale_ciclo_iniziato_oggi
      - button.ciclo_mestruale_ciclo_finito_oggi
```

Promemoria due giorni prima del ciclo previsto:

```yaml
alias: Promemoria ciclo
triggers:
  - trigger: numeric_state
    entity_id: sensor.ciclo_mestruale_giorni_al_prossimo_ciclo
    below: 3
conditions:
  - condition: numeric_state
    entity_id: sensor.ciclo_mestruale_giorni_al_prossimo_ciclo
    above: 0
actions:
  - action: notify.notify
    data:
      message: >
        Il ciclo è previsto tra
        {{ states('sensor.ciclo_mestruale_giorni_al_prossimo_ciclo') }} giorni.
```

I nomi delle entità dipendono dal nome che hai dato all'integrazione e dalla lingua di Home Assistant.

---

## English

A custom integration that keeps a **menstrual cycle calendar** in Home Assistant: log when your period starts and it predicts the next one, ovulation and the fertile window.

> **Warning:** predictions are statistical estimates based on the logged cycles. They are not medical advice and **must not be used as contraception**.

It includes a **dashboard card** (`custom:menstrual-cycle-card`, listed in the card picker with a preview, no resource to add) showing a gauge of the cycle days with the period, the fertile window, ovulation and today. It also provides a calendar (logged and expected periods, fertile windows, ovulation; periods can be added or deleted from the calendar card), sensors (next period, days until next period, ovulation, fertile window start/end, phase, cycle day, last period, average cycle and period length), binary sensors (*Period*, *Fertile window*), buttons (*Period started today*, *Period ended today*) and the actions `menstrual_cycle.log_period_start`, `log_period_end`, `add_period` and `delete_period`.

The cycle length is the average of the last N logged cycles (6 by default, gaps outside 15–60 days are ignored). Ovulation is estimated as the next period minus the luteal phase (14 days by default); the fertile window spans the 5 days before ovulation to the day after.

Install via HACS as a custom repository (category *Integration*) or copy `custom_components/menstrual_cycle` into your `config/custom_components` folder, restart, then add **Menstrual Cycle** from *Settings → Devices & services*.

## License

[MIT](LICENSE)
