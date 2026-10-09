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
- **Pulsanti**: *Ciclo iniziato oggi*, *Ciclo finito oggi*, *Test LH positivo oggi*, *Ovulazione oggi*.
- **Azioni**: `menstrual_cycle.log_period_start`, `log_period_end`, `add_period`, `delete_period`, `log_ovulation`, `delete_ovulation`.
- **Statistiche**: fase luteale e follicolare personali, variabilità del ciclo e dell'ovulazione, storico degli ultimi 12 cicli.
- Interfaccia in italiano e inglese. I dati restano solo nel tuo Home Assistant.

## Come calcola le previsioni

- **Durata del ciclo**: media degli ultimi N cicli registrati (6 di default). Gli intervalli fuori da 15–60 giorni vengono ignorati perché probabilmente manca una registrazione. Finché non ci sono almeno due cicli si usa la durata impostata.
- **Prossimo ciclo**: inizio dell'ultimo ciclo + durata media. Se l'ovulazione del ciclo in corso è registrata: ovulazione + fase luteale personale, che è più preciso.
- **Ovulazione**: prossimo ciclo − fase luteale personale.
- **Finestra fertile**: dai 5 giorni prima dell'ovulazione al giorno dopo, allargata di 1–3 giorni per lato se i cicli passati sono irregolari.

### Registrare l'ovulazione

Oltre a inizio e fine ciclo puoi registrare l'ovulazione:

- pulsante **Test LH positivo oggi**: l'ovulazione viene stimata il giorno dopo;
- pulsante **Ovulazione oggi**: per ecografia, sintomi o quando sei sicura del giorno;
- azione `menstrual_cycle.log_ovulation`, con data e metodo (test LH, rialzo della temperatura basale, ecografia, sintomi, altro), anche per i cicli passati.

Ogni ciclo tiene una sola ovulazione: registrarne un'altra nello stesso ciclo la sostituisce. Le ovulazioni compaiono nel calendario e si possono eliminare da lì.

### Perché migliora la previsione

Il ciclo ha due fasi: la **follicolare** (dalle mestruazioni all'ovulazione) e la **luteale** (dall'ovulazione al ciclo successivo). Gli studi mostrano che la variabilità della durata del ciclo dipende soprattutto dalla fase follicolare, mentre quella luteale cambia meno nella stessa donna (in media circa 12–14 giorni, ma con differenze personali tra 7 e 17). Per questo l'integrazione:

1. impara la **tua fase luteale** dai cicli con ovulazione registrata (luteale = inizio ciclo successivo − ovulazione). Parte dal valore impostato e si sposta verso la tua media man mano che i dati crescono, così un solo ciclo anomalo non stravolge tutto;
2. prevede l'ovulazione **all'indietro** dal ciclo atteso: prossimo ciclo − fase luteale personale;
3. quando l'ovulazione del ciclo in corso è registrata, prevede il ciclo successivo **in avanti** da lì, invece che dalla durata media;
4. misura quanto varia il giorno dell'ovulazione (deviazione standard della fase follicolare, o della durata del ciclo finché non ci sono almeno 3 ovulazioni registrate) e **allarga la finestra fertile** di conseguenza.

Cosa può spostare l'ovulazione da un ciclo all'altro: stress, malattie e febbre, viaggi e cambi di fuso, sonno scarso, attività fisica intensa, variazioni di peso, sospensione della contraccezione ormonale, allattamento, età (la fase follicolare si accorcia con gli anni), condizioni come PCOS o problemi alla tiroide. Il rialzo della temperatura basale conferma l'ovulazione solo dopo che è avvenuta; il test LH la anticipa di circa un giorno.

### Statistiche e storico

Sensori con statistiche a lungo termine, utilizzabili nei grafici di Home Assistant:

- **Durata media del ciclo**, con l'attributo `cycles`: gli ultimi 12 cicli completi con durata, mestruazioni, data dell'ovulazione, fase follicolare e luteale;
- **Durata media delle mestruazioni**;
- **Durata fase luteale** (personale) e **Durata fase follicolare**;
- **Variabilità del ciclo** e **Variabilità dell'ovulazione** (deviazione standard in giorni: più è bassa, più la previsione è affidabile).

Il sensore **Ovulazione** ha gli attributi `confirmed` (ovulazione registrata), `variability_days` e `fertile_window_margin_days`.

Fonti principali:

- Bull J.R. et al., *Real-world menstrual cycle characteristics of more than 600,000 menstrual cycles*, npj Digital Medicine, 2019 ([PMC6710244](https://pmc.ncbi.nlm.nih.gov/articles/PMC6710244/)): fase follicolare media 16,9 giorni, luteale 12,4; la fase follicolare si accorcia con l'età.
- Henry S. et al., *Prospective 1-year assessment of within-woman variability of follicular and luteal phase lengths*, Human Reproduction, 2024 ([articolo](https://academic.oup.com/humrep/article/39/11/2565/7775370)): la fase follicolare varia più di quella luteale, ma anche la luteale non è fissa.
- Studio WHO sull'intervallo tra picco di LH e ovulazione (mediana circa 16–32 ore), citato in [Clearblue, *Evidence for using LH+1*](https://se.clearblue.com/sites/default/files/HCP_Publications/Articles-Pregnancy/Evidence_for_using_LH%2B1_as_marker_for_conception.pdf).

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

The cycle length is the average of the last N logged cycles (6 by default, gaps outside 15–60 days are ignored). Ovulation is estimated as the next period minus the personal luteal phase; the fertile window spans the 5 days before ovulation to the day after, widened when past cycles are irregular.

You can also log ovulation (buttons *Positive LH test today* and *Ovulation today*, or the `log_ovulation` action with date and method). Since the luteal phase varies less than the follicular phase within a woman, the logged ovulations are used to learn the personal luteal phase (shrunk towards the configured value while data is scarce); once the current cycle's ovulation is logged, the next period is predicted from it. Sensors expose the personal luteal and follicular phase, cycle and ovulation variability (standard deviation) and the last 12 cycles, with long-term statistics.

Install via HACS as a custom repository (category *Integration*) or copy `custom_components/menstrual_cycle` into your `config/custom_components` folder, restart, then add **Menstrual Cycle** from *Settings → Devices & services*.

## License

[MIT](LICENSE)
