# Architektur

## Überblick

```
Provider-Event (z. B. FR24-Bus-Event)
        │
        ▼
  backends/fr24.py  (Source-Adapter: Event → normalisiertes Modell)
        │  Entry / Sighting / Movement  (models.py)
        ▼
  coordinator.py  (SkywatchCoordinator, DataUpdateCoordinator)
        │  persistiert über storage/*, feuert `skywatch_sighting`-Event
        ▼
  storage/  (reines sqlite3, synchron, in Executor-Thread gekapselt)
        │
        ▼
  data_builder.py  (führt alle Dashboard-Abfragen aus, baut ein dict)
        │
        ▼
  sensor.py / binary_sensor.py / number.py / text.py / switch.py / button.py
        │
        ▼
  Home Assistant Entities  +  http.py (GeoJSON + Live-Karte)
```

## Komponenten

### Backend-Adapter (`backends/`)

- `backends/base.py` definiert die abstrakte Klasse `Source` mit vier Listener-Typen: `on_entry`, `on_exit`, `on_landing`, `on_takeoff`.
- `backends/fr24.py` ist die konkrete Implementierung für die HACS-Integration *Flightradar24* (`AlexandrErohin/home-assistant-flightradar24`). Sie abonniert vier HA-Bus-Events (`flightradar24_entry`, `flightradar24_exit`, `flightradar24_area_landed`, `flightradar24_area_took_off`) und übersetzt deren Rohdaten in die normalisierten Modelle `Entry`, `Sighting`, `Movement` (`models.py`).
- `current_flights()` liefert eine Live-Momentaufnahme der aktuell im Gebiet befindlichen Flugzeuge – bei FR24 aus dem Attribut `flights` von `sensor.flightradar24_current_in_area`.
- `watched_entities()` gibt HA-Entity-IDs zurück, deren Zustandsänderung sofort eine Positionserfassung auslösen soll (bei FR24: eben dieser Sensor) – das halbiert die Latenz zwischen „neue Quelldaten“ und „Marker bewegt sich auf der Karte“.
- Das Adapter-Muster ist bewusst so gebaut, dass weitere Quellen (dump1090, tar1090, ADSB-Hub …) nur eine neue Datei erfordern; Storage, Coordinator und Plattformen bleiben unverändert.

### Coordinator (`coordinator.py`)

`SkywatchCoordinator` erbt von Home Assistants `DataUpdateCoordinator` und übernimmt zwei Rollen:

1. **Event-Brücke**: registriert sich bei den vier Source-Listenern. Da Backend-Callbacks aus einem Worker-Thread kommen können, springt jeder Handler zunächst per `hass.loop.call_soon_threadsafe` auf den Event-Loop, bevor er `hass.bus.async_fire` oder `hass.async_create_task` aufruft (beide sind Event-Loop-only-APIs).
2. **Datenaktualisierung**: alle 30 s (`UPDATE_INTERVAL`) baut `_async_update_data` über `data_builder.build_data` das komplette Datendict neu auf; die Sensoren lesen daraus.

Zusätzlich läuft ein **schneller Trail-Erfassungs-Timer** alle 5 s (`TRAIL_CAPTURE_INTERVAL`), der die Positionen aller aktuell aktiven Flüge in `flight_positions` schreibt und ältere Punkte (>30 min) prunt – unabhängig vom 30-Sekunden-Refresh, weil die Kartendarstellung feinere Auflösung braucht.

Bei jedem `entry`/`exit`/`landed`/`took_off`-Ereignis feuert der Coordinator zusätzlich das generische HA-Event `skywatch_sighting` (siehe [events-und-blueprints.md](events-und-blueprints.md)) und persistiert parallel in SQLite.

Der Coordinator hält außerdem den UI-Zustand für Pagination (`current_page`) und Suchbegriff (`current_search_term`), gesteuert über `number.skywatch_sightings_page` bzw. `text.skywatch_search_term` oder die gleichnamigen Services.

### Storage (`storage/`)

- Reines, synchrones `sqlite3` – keine HA-Importe, dadurch in Unit-Tests direkt gegen `tmp_path`-Datenbanken testbar.
- `connection.py` öffnet die DB und wendet Migrationen an (`open_db`).
- `schema.py` definiert das v1-Schema (Tabellen `sightings`, `entries`, `airport_movements`, `flight_positions`) inklusive aller Indizes.
- `migrations.py` hebt ältere/legacy Datenbanken auf den aktuellen `PRAGMA user_version` an.
- `queries.py` enthält alle Leseabfragen für das Dashboard (siehe [datenhaltung.md](datenhaltung.md)).
- `repository.py` bündelt Schreiboperationen (Insert/Prune) für Entries, Sightings, Movements und Positionen.
- `normalizers.py` enthält Hilfsfunktionen wie `coerce_int`, `coerce_float`, `normalize_photo_url` (behebt kaputte `https:https://`-URLs aus älteren FR24-Builds).

Der Coordinator kapselt jeden SQLite-Zugriff in `hass.async_add_executor_job`, damit blockierendes I/O nie den Event-Loop stoppt.

### Datenmodelle (`models.py`)

Drei unveränderliche (`frozen`) Dataclasses bilden die Schnittstelle zwischen Backend und Storage:

- **`Entry`** – ein Flugzeug, das gerade in den Beobachtungsradius eingeflogen ist (transient, wird nach 2 h TTL gelöscht, falls kein passender Exit folgt).
- **`Sighting`** – eine abgeschlossene Durchquerung des Beobachtungsradius (der persistente Datensatz).
- **`Movement`** – ein Start oder eine Landung an einem beobachteten Flughafen.

### Klassifizierung (`classify.py`)

Reine Python-Logik ohne HA-Abhängigkeit für:

- `is_helicopter` / `is_military` – Abgleich des ICAO-Typcodes gegen die konfigurierten Code-Listen (case-insensitive).
- `WatchEntry` + `match_watch` – generisches Watchlist-Matching nach Registrierung oder FR24-Privacy-Block-Fingerabdruck (siehe [klassifizierung.md](klassifizierung.md)).

### Plattformen

Sechs HA-Plattformen werden in `__init__.py::PLATFORMS` registriert: `sensor`, `binary_sensor`, `number`, `text`, `switch`, `button`. Alle Entities hängen am selben `Skywatch`-Gerät (`_device.py::build_device_info`).

### HTTP-Schicht (`http.py`)

Zwei unauthentifizierte `HomeAssistantView`s für die Live-Karte:

- `GET /api/skywatch/flights.geojson` – GeoJSON-FeatureCollection der aktuell im Gebiet befindlichen Flugzeuge plus Trail-Polylinien.
- `GET /api/skywatch/map` – liefert die statische Leaflet-Seite aus `www/skywatch-map.html`.

Details siehe [live-karte.md](live-karte.md).

### Setup-Lebenszyklus (`__init__.py`)

- `async_setup_entry` liest die zusammengeführte Config (`entry.data` + `entry.options`), baut `Fr24Source` und `SkywatchCoordinator`, ruft `coordinator.async_setup()` auf und reicht den Entry an die sechs Plattformen weiter.
- Services (`skywatch.*`) und die beiden HTTP-Views werden nur beim **ersten** Config Entry registriert und beim **letzten** Unload wieder entfernt – Skywatch ist als Single-Instance-Integration gedacht (`SINGLETON_UNIQUE_ID` im Config Flow), technisch aber mehrfach-Entry-fähig vorbereitet.
- Jede Änderung im Options Flow löst über einen `add_update_listener` einen kompletten Reload des Config Entry aus – bewusst einfach gehalten, weil Watchlist, ICAO-Codes und Schwellwerte fest in den Coordinator-Zustand einfließen.
