# Klassifizierung (`classify.py`)

Reine Python-Logik ohne Home-Assistant-Abhängigkeit — löst die alten ha-tinker-Jinja-Makros (`helo_codes()`, `is_regina_police_unit()`) ab, die als Custom-Templates nicht HACS-distributierbar waren. Die Klassifizierung läuft jetzt serverseitig in der Integration und wird über Sensoren, Binary Sensors, das GeoJSON und das `skywatch_sighting`-Event ausgespielt.

## Hubschrauber- und Militär-Erkennung

```python
is_helicopter(aircraft_code, helo_codes) -> bool
is_military(aircraft_code, military_codes) -> bool
```

Beide vergleichen den ICAO-Typcode case-insensitive gegen die konfigurierte Code-Liste (Default oder per Options Flow überschrieben, siehe [konfiguration.md](konfiguration.md)). Ein leerer/`None`-Code gilt immer als „nein“.

Verwendung:

- `binary_sensor.skywatch_helicopter_overhead` (Live-Check über alle aktuell im Gebiet befindlichen Flugzeuge)
- `sensor.skywatch_military_sightings` (historische Abfrage, `query_military`)
- GeoJSON-Feature-Properties `is_helo` / `is_military` (Live-Karte)
- `skywatch_sighting`-Event-Payload

## Watchlist-Matching

```python
@dataclass(frozen=True)
class WatchEntry:
    slug: str
    label: str
    registration: str | None = None
    aircraft_code: str | None = None
    match_blocked: bool = False
```

Ist die Verallgemeinerung von `is_regina_police_unit`: Statt eine feste Registrierung (`C-GRPF`) hart zu kodieren, kann der Nutzer beliebig viele Watch-Einträge über den Options Flow anlegen.

`match_watch(flight, watch_entries)` prüft pro Eintrag **in Konfigurationsreihenfolge** zwei Kriterien und gibt den ersten Treffer zurück:

1. **Registrierungs-Treffer** – `entry.registration` (case-insensitive) entspricht der `aircraft_registration`/`registration` des Flugs.
2. **Blocked-Fingerabdruck** – nur wenn `entry.match_blocked` gesetzt ist: `entry.aircraft_code` entspricht dem ICAO-Typcode **und** der Callsign ist exakt `"Blocked"` **und** keine Registrierung vorliegt. Damit lassen sich Luftfahrzeuge erkennen, die FR24 aus Datenschutzgründen ohne Registrierung/Callsign anzeigt (Ursprungsfall: Regina Police Air Unit C-GRPF).

`slug` bestimmt den Entity-ID-Suffix (`sensor.skywatch_watch_<slug>`, siehe [entities.md](entities.md)); `label` ist der für Menschen lesbare Anzeigename.

`WatchEntry.from_dict` baut den Eintrag aus dem im Options Flow gespeicherten Dict (validiert nur das Vorhandensein von `slug`).

## Wo das Matching überall greift

- **Coordinator** (`coordinator.py::_fire_skywatch_event`): reichert jedes gefeuerte `skywatch_sighting`-Event mit `watch_slug`/`watch_label` an.
- **Data Builder** (`data_builder.py`): baut pro Watch-Eintrag über `query_watch_aircraft` den Datenblock für den zugehörigen Sensor.
- **HTTP/GeoJSON** (`http.py`): markiert jedes Live-Feature mit `watch_slug`/`watch_label`, damit die Karte Watchlist-Treffer in Lila hervorheben kann.
