# Entities

Alle Entities hängen an genau einem Gerät `Skywatch` (`_device.py`) und nutzen `_attr_has_entity_name = True`, sodass HA den Anzeigenamen aus Gerätename + Entity-Name zusammensetzt.

## Sensoren (`sensor.py`)

12 statisch definierte Sensoren + N Watchlist-Sensoren. Alle lesen aus dem vom Coordinator alle 30 s gebauten Datendict (`data_builder.build_data`), außer `flights_in_area`, der live aus der Quelle liest.

| Entity-Key | Name | Wert | Attribute | Kategorie |
|---|---|---|---|---|
| `log_today` | Sightings today | Anzahl heutiger Sichtungen | – | normal |
| `log_this_week` | Sightings this week | Anzahl Sichtungen diese Woche | – | normal |
| `active_last_1h` | Active last 1h | Sichtungen der letzten Stunde **+** aktuell im Gebiet befindliche Flugzeuge | – | normal |
| `active_last_24h` | Active last 24h | wie oben für 24 h | – | normal |
| `log_recent` | Recent sightings | Anzahl der Zeilen auf der aktuellen Seite | Liste der letzten Sichtungen (Rohdaten, paginiert) | diagnostic |
| `log_search` | Search results | Trefferanzahl | Liste der Treffer für den aktuellen Suchbegriff | diagnostic |
| `log_stats` | Sightings all-time | Gesamtanzahl | weitere Statistik-Felder (siehe `query_stats`) | normal |
| `log_top_routes` | Top routes | Anzahl Routen | Liste der häufigsten Origin/Destination-Paare | diagnostic |
| `log_overhead` | Overhead sightings | Anzahl Overhead-Transits | Liste der Overhead-Sichtungen | diagnostic |
| `log_hour_histogram` | Sightings hour-of-day | – | 24-Stunden-Histogramm der Sichtungen | diagnostic |
| `military_sightings` | Military sightings | Anzahl militärischer Sichtungen | Liste der militärischen Sichtungen | diagnostic |
| `helicopter_sightings` | Helicopter sightings | Anzahl Sichtungen mit ICAO-Code aus der Hubschrauber-Liste | Liste der Hubschrauber-Sichtungen | diagnostic |
| `airplane_sightings` | Airplane sightings | Anzahl Sichtungen, deren ICAO-Code **nicht** in der Hubschrauber-Liste steht | Liste der Flugzeug-Sichtungen | diagnostic |
| `movements_today` | Airport movements today | Anzahl Starts/Landungen heute | Liste der Bewegungen | diagnostic |
| `flights_in_area` | Aircraft in area | Live-Anzahl (`len(source.current_flights())`) | – | normal |

Für alle Sensoren mit Listen-Attribut wird `count` aus den Attributen herausgefiltert (`_attrs_excluding_count`), da der Wert selbst schon die Zählung trägt.

`helicopter_sightings` und `airplane_sightings` bilden zusammen eine vollständige, sich gegenseitig ausschließende Aufteilung aller Sichtungen nach der konfigurierten Hubschrauber-Codeliste (`query_helicopters` / `query_planes` in `storage/queries.py`, siehe [datenhaltung.md](datenhaltung.md)): jede Sichtung landet in genau einem der beiden. `airplane_sightings` schließt militärisches Starrflügel-Fluggerät mit ein — `military_sightings` bleibt eine eigene, damit **überlappende** Kategorie (ein Militärjet zählt sowohl bei „Airplane“ als auch bei „Military“).

### Watchlist-Sensoren (`SkywatchWatchSensor`)

Für jeden konfigurierten Watch-Eintrag entsteht `sensor.skywatch_watch_<slug>`:

- **Zustand**: Gesamtanzahl (lifetime) der Sichtungen, die auf diesen Watch-Eintrag gematcht haben.
- **Attribute**: Details der letzten Sichtung (alles außer `count`), z. B. letzte Sichtzeit, Callsign, Höhe usw.

## Binary Sensors (`binary_sensor.py`)

Beide lesen **live** aus `source.current_flights()` – nicht aus dem 30-Sekunden-Datendict – und reagieren daher unmittelbar auf Zustandsänderungen der Quelle:

| Entity | Bedeutung |
|---|---|
| `binary_sensor.skywatch_has_aircraft` (Aircraft present) | `on`, sobald mindestens ein Flugzeug im Beobachtungsradius ist |
| `binary_sensor.skywatch_helicopter_overhead` (Helicopter overhead) | `on`, sobald mindestens ein im Radius befindliches Flugzeug einen konfigurierten Hubschrauber-ICAO-Code trägt; Attribut `helicopters` listet die betroffenen Callsigns |

## Steuer-Entities

Native Entities statt YAML-`input_*`-Helfer – sie erscheinen automatisch unter **Einstellungen → Geräte & Dienste → Skywatch**, persistieren über die Entity Registry und benötigen keine Nutzer-YAML.

| Entity | Plattform | Zweck |
|---|---|---|
| `number.skywatch_sightings_page` | `number.py` | Pagination-Cursor für „Recent sightings“ (1–9999, Box-Modus mit +/‑-Steuerung); Setzen ruft `coordinator.async_set_page` |
| `text.skywatch_search_term` | `text.py` | Freitext-Filter für `sensor.skywatch_log_search`; Setzen ruft `coordinator.async_set_search_term` |
| `switch.skywatch_alerts_enabled` | `switch.py` | Master-Schalter zum Stummschalten aller Aircraft-Alarme; Zustand übersteht Neustarts (`RestoreEntity`), Default „on“ |
| `button.skywatch_clear_search` | `button.py` | Setzt den Suchbegriff mit einem Klick auf leer zurück |

Die Steuer-Entities greifen nicht selbst in die Automatisierungslogik ein – Blueprints referenzieren z. B. `switch.skywatch_alerts_enabled` als Enable-Toggle (siehe [events-und-blueprints.md](events-und-blueprints.md)).

## Empfohlener Recorder-Ausschluss

Sensoren mit Listen-Attributen tragen 5–15 KB Payload und überschreiten leicht Home Assistants 16-KB-Attribut-Grenze. Das Repository liefert eine fertige `recorder.exclude`-Empfehlung, siehe [`docs/RECORDER_EXCLUDE.md`](../RECORDER_EXCLUDE.md) und die README.
