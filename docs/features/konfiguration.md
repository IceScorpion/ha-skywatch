# Konfiguration

## Config Flow (Ersteinrichtung)

`config_flow.py::SkywatchConfigFlow`, Schritt `user`:

| Feld | Typ | Pflicht | Default | Validierung |
|---|---|---|---|---|
| Heimat-Breitengrad (`home_latitude`) | float | ja | HA-Standort-Breitengrad | −90 … 90 |
| Heimat-Längengrad (`home_longitude`) | float | ja | HA-Standort-Längengrad | −180 … 180 |
| Flughafen-IATA-Code (`airport_iata`) | string | optional | leer | genau 3 Buchstaben, wird großgeschrieben |
| Radius in km (`radius_km`) | int | ja | 50 | – |

Zusätzliche Abbruchbedingung: Ist die **Flightradar24-HACS-Integration** nicht konfiguriert, bricht der Flow mit dem Fehler `fr24_not_loaded` ab (Skywatch setzt aktuell zwingend FR24 als Datenquelle voraus).

Die Integration ist als **Singleton** angelegt: `async_set_unique_id(SINGLETON_UNIQUE_ID)` + `_abort_if_unique_id_configured()` verhindern eine doppelte Einrichtung. Nach erfolgreicher Einrichtung wird zusätzlich `source: "fr24"` in den Entry-Daten hinterlegt.

## Options Flow (nachträgliche Konfiguration)

`config_flow.py::SkywatchOptionsFlowHandler` – erreichbar über **Einstellungen → Geräte & Dienste → Skywatch → Konfigurieren**. Menügeführt mit drei Untermenüs:

### 1. Watchlist (`watch_list`)

- **Eintrag hinzufügen** (`add_watch`): `slug` (Pflicht, Muster `^[a-z0-9_]+$`), `label` (optional, fällt auf den Slug zurück), `registration`, `aircraft_code`, `match_blocked` (Checkbox).
  - Validierungsfehler: `invalid_slug`, `slug_exists`, `watch_entry_needs_criteria` (mindestens eines von Registrierung / ICAO-Code / „Blocked“-Fingerabdruck muss gesetzt sein).
- **Eintrag entfernen** (`remove_watch`): Auswahl aus einer Dropdown-Liste der bestehenden Slugs.
- Jeder Watchlist-Eintrag erzeugt automatisch einen eigenen Sensor `sensor.skywatch_watch_<slug>` (siehe [entities.md](entities.md)) und wird beim Matching von Sichtungen berücksichtigt (siehe [klassifizierung.md](klassifizierung.md)).

### 2. ICAO-Code-Listen (`codes`)

- **Hubschrauber-Codes** (`helo_codes`) und **Militär-Codes** (`military_codes`) werden als kommagetrennter Freitext eingegeben (`"a109, b06,c130"`) und über `_parse_codes` normalisiert (getrimmt, großgeschrieben, dedupliziert, sortiert).
- Defaults: 84 vordefinierte Hubschrauber-ICAO-Typcodes (`DEFAULT_HELO_CODES`) bzw. rund 50 militärische Typcodes (`DEFAULT_MILITARY_CODES`), siehe `const.py`.
- Eine Änderung hier ersetzt die Default-Liste vollständig (kein Merge) – Nutzer, die die Defaults erweitern wollen, müssen die vorbelegte Liste im Textfeld stehen lassen und ergänzen.

### 3. Schwellwerte & Alarme (`thresholds`)

| Feld | Const | Default | Zweck |
|---|---|---|---|
| Overhead-Distanz (km) | `overhead_distance_km` | 5 | Ab welcher Nähe eine Sichtung als „Overhead-Transit“ zählt |
| Overhead-Höhe (ft) | `overhead_altitude_ft` | 10 000 | Zusätzliches Höhenkriterium für „Overhead“ |
| Alarme aktiviert | `alerts_enabled` | true | Wird aktuell nur als Optionswert gespeichert; die eigentliche Umschaltung im laufenden Betrieb erfolgt über `switch.skywatch_alerts_enabled` |
| Quiet-Hours Start/Ende | `quiet_hours_start` / `quiet_hours_end` | leer | Freitextfelder, aktuell nicht in der Coordinator-Logik ausgewertet (siehe „Roadmap“ im README: geplant als Zeit-Entities) |

Jede Änderung in einem der drei Untermenüs speichert sofort per `async_create_entry(title="", data=new_options)` und löst – wie im Options-Flow für ConfigEntries üblich – über den in `__init__.py` registrierten `add_update_listener` einen vollständigen Reload der Integration aus.

## Zusammenspiel von `entry.data` und `entry.options`

`__init__.py` führt bei jedem Setup `{**entry.data, **entry.options}` zusammen: Werte aus dem Options Flow überschreiben die ursprüngliche Ersteinrichtung. Das betrifft insbesondere `watch_list`, `helo_codes`, `military_codes`, `overhead_distance_km` und `overhead_altitude_ft`, die direkt als Konstruktor-Parameter in `SkywatchCoordinator` einfließen.
