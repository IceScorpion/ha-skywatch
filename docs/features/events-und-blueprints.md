# Events und Blueprints

## Das Event `skywatch_sighting`

Der Coordinator feuert bei jedem Lifecycle-Ereignis ein **quellen-unabhängiges** HA-Event auf den Bus (`EVENT_SKYWATCH_SIGHTING = "skywatch_sighting"`), statt dass Automatisierungen sich direkt an FR24-spezifische Events hängen. Wechselt man später das Backend (dump1090, tar1090 …), bleiben bestehende Automatisierungen unverändert funktionsfähig.

Ausgelöst wird es aus vier Stellen im Coordinator (`_on_entry_on_loop`, `_on_exit_on_loop`, `_on_landing_on_loop`, `_on_takeoff_on_loop`), jeweils **auf dem Event-Loop** (nicht aus dem Backend-Worker-Thread).

### Payload

| Feld | Typ | Bedeutung |
|---|---|---|
| `kind` | string | `"entry"` \| `"exit"` \| `"landed"` \| `"took_off"` |
| `flight_id` | string\|null | Tracking-ID der Quelle (nur bei `entry`/`exit` gesetzt) |
| `callsign` | string\|null | |
| `aircraft_code` | string\|null | ICAO-Typcode |
| `aircraft_model` | string\|null | Klartext-Modellbezeichnung |
| `registration` | string\|null | Kennzeichen (bei `entry` immer `null`, da FR24 es erst beim Exit liefert) |
| `is_helo` | bool | Ergebnis von `classify.is_helicopter` |
| `is_military` | bool | Ergebnis von `classify.is_military` |
| `watch_slug` | string\|null | Slug des gematchten Watchlist-Eintrags, falls einer zutrifft |
| `watch_label` | string\|null | zugehöriges Label |

## Mitgelieferte Blueprints (`blueprints/automation/skywatch/`)

Alle drei sind über eine Blueprint-URL direkt importierbar (siehe README → „Blueprints“).

### 1. Aircraft entry alert (`aircraft-entry-alert.yaml`)

Benachrichtigt bei jedem `skywatch_sighting`-Event mit `kind: entry`.

- **Eingaben**: optionaler `enable_toggle` (ein `input_boolean`, z. B. `switch.skywatch_alerts_enabled`), `helo_only` / `military_only` als Boolean-Filter, `notify_service`, `notify_title` (Default „Aircraft entering area“).
- **Bedingungen**: Toggle muss leer oder `on` sein; ist `helo_only` gesetzt, muss `trigger.event.data.is_helo` wahr sein (analog für `military_only`).
- **Nachricht**: `"<Callsign> (<Modell oder ICAO-Code>) entered the skywatch radius."`

### 2. Watch-list match alert (`watch-list-match-alert.yaml`)

Benachrichtigt, wenn ein Watchlist-Eintrag getroffen wurde.

- **Eingaben**: optionaler `watch_slug` (leer = jeder Treffer), `on_kinds` (Mehrfachauswahl aus `entry`/`exit`/`landed`/`took_off`, Default nur `entry`), `notify_service`.
- **Bedingungen**: `watch_slug` im Event darf nicht `null` sein (= es gab überhaupt einen Watch-Treffer); passt zum optional gewählten Slug; `kind` ist in der gewählten Menge enthalten.
- **Nachricht**: Titel = Watch-Label (oder Slug); Text = `"<Kind, groß> — <Callsign oder ICAO-Code> (<Modell>)."`

### 3. Daily digest (`daily-digest.yaml`)

Zeitgesteuerte Tageszusammenfassung, standardmäßig 19:00 Uhr lokal.

- **Eingaben**: `digest_time`, `notify_service`, sowie die vier Sensor-Entities, aus denen die Zusammenfassung gelesen wird (`today_sensor`, `overhead_sensor`, `military_sensor`, `stats_sensor` — jeweils mit sinnvollen Defaults vorbelegt).
- **Trigger**: `platform: time` auf `digest_time`.
- **Nachricht**: Sichtungen heute, Overhead-Anzahl, Militär-Anzahl sowie die Top-Airlines aus dem Attribut `top_airlines` des Stats-Sensors.

Alle drei Blueprints greifen ausschließlich auf öffentlich dokumentierte Sensor-Zustände/-Attribute bzw. das `skywatch_sighting`-Event zurück — sie funktionieren unabhängig davon, welches Backend gerade konfiguriert ist.
