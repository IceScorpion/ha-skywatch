# Datenhaltung

Skywatch persistiert vollständig in einer eigenen SQLite-Datei unter `<config>/skywatch/sightings.db` (`DB_SUBDIR` = `skywatch`, `DB_FILENAME` = `sightings.db`). Die Storage-Schicht ist reines, synchrones `sqlite3` ohne Home-Assistant-Importe — dadurch sind alle Abfragen isoliert gegen eine `tmp_path`-Datenbank testbar.

## Schema (`storage/schema.py`, `SCHEMA_VERSION = 1`)

Vier Tabellen, alle mit Indizes für die üblichen Dashboard-Abfragen:

| Tabelle | Zweck | wichtige Indizes |
|---|---|---|
| `sightings` | Abgeschlossene Durchquerungen des Beobachtungsradius (der historische Log) | `exit_time`, `callsign`, `airline_iata`, `aircraft_code`, `(altitude_ft, closest_km)`, `origin_iata`, `destination_iata`, `registration` |
| `entries` | Transiente „gerade eingeflogen“-Datensätze, PK = `flight_id` | `entry_time` |
| `airport_movements` | Starts/Landungen an beobachteten Flughäfen | `event_time`, `airport_iata`, `direction` |
| `flight_positions` | Zeitstempel-Positionspunkte für die Live-Karten-Trails, PK = `(flight_id, ts)` | `ts`, `flight_id` |

Diese Indizes fehlten in der ursprünglichen ha-tinker-Datenbank; Skywatch legt sie unbedingt an, damit Militär-/Overhead-/Routen-Abfragen nicht mehr auf Full-Table-Scans laufen.

## Migrationen (`storage/migrations.py`)

Vorwärtsgerichtete, idempotente Migrationsleiter über `PRAGMA user_version`:

- Legacy-Datenbanken (ha-tinker `sky_sightings.db`) starten bei `user_version = 0`, da dort nie eine PRAGMA gesetzt wurde.
- `_migrate_0_to_1` führt das v1-DDL per `executescript` aus (bei Neuinstallation entsteht so das komplette Schema; bei Legacy-DBs ergänzt `CREATE INDEX IF NOT EXISTS` nur die fehlenden Indizes), fügt fehlende Spalten (`entry_time`, `heading`, `vertical_speed`, `on_ground`) per `ALTER TABLE` hinzu und bereinigt einmalig kaputte `https:https://`-Foto-URLs, die ältere FR24-Builds erzeugt haben.
- `run_migrations` wird beim Öffnen der Verbindung (`connection.py::open_db`) automatisch aufgerufen und hebt die DB Schritt für Schritt bis `SCHEMA_VERSION` an.

## Schreiboperationen (`storage/repository.py`)

Wird ausschließlich vom Coordinator aufgerufen, jeweils in einem Executor-Thread:

- `insert_entry` / `take_entry_time` / `prune_stale_entries` — Verwaltung der transienten `entries`-Tabelle (TTL: `DEFAULT_ENTRY_TTL_HOURS = 2`).
- `insert_sighting` — schreibt eine abgeschlossene Sichtung; übernimmt die `entry_time` aus dem passenden `entries`-Datensatz, falls vorhanden.
- `insert_movement` — schreibt Start/Landung.
- `insert_positions` / `prune_old_positions` / `fetch_trails` — Positions-Sampling für die Live-Karten-Trails (30-Minuten-Fenster).

## Leseabfragen (`storage/queries.py`)

Portiert aus dem ursprünglichen `sky-log-query.py`-Skript; die Rückgabe-Dict-Form ist bewusst kompatibel zu den bestehenden ha-tinker-Dashboards gehalten (Skywatch soll ein Drop-in-Replacement sein, keine Neuarchitektur, die Dashboards zum Umschreiben zwingt).

| Funktion | Liefert |
|---|---|
| `query_today` | Anzahl Sichtungen seit lokaler Mitternacht |
| `query_active_1h` / `query_active_24h` | Rollierendes Zeitfenster (letzte 1 h / 24 h), unabhängig vom Mitternachts-Cutoff |
| `query_recent` | Paginierte Liste aller Sichtungen (`page`, `page_size=40`) inkl. `total_pages`/`total_count` |
| `query_search` | Volltextsuche über Callsign, Flugnummer, Airline, Registrierung, Origin/Destination-IATA, ICAO-Code und Modell (case-insensitive, `LIKE`) |
| `query_stats` | Gesamtanzahl, heute, diese Woche, Top-10-Airlines, Top-10-Flugzeugmuster, „seltene“ Muster (≤2 Sichtungen) |
| `query_top_routes` | Top-10 Origin/Destination-Paare |
| `query_overhead` | Sichtungen unterhalb der konfigurierten Distanz- **und** Höhenschwelle |
| `query_military` | Sichtungen, deren ICAO-Code in der konfigurierten Militärliste steht |
| `query_helicopters` | Sichtungen, deren ICAO-Code in der konfigurierten Hubschrauber-Liste steht (analog zu `query_military`, gleiche Rückgabeform) |
| `query_planes` | Sichtungen, deren ICAO-Code **nicht** in der Hubschrauber-Liste steht — komplementär zu `query_helicopters`, schließt militärisches Starrflügel-Fluggerät ein; bei leerer Hubschrauber-Liste zählen alle Sichtungen als „Plane“ |
| `query_hour_histogram` | 24-Stunden-Bucket-Zählung, Zeitzonen-korrekt in Python berechnet (nicht in SQL, damit DST-Wechsel keine falschen Zahlen erzeugen) |
| `query_movements_today` | Starts/Landungen seit lokaler Mitternacht, getrennt nach Richtung gezählt |
| `query_watch_aircraft` | Pro-Watch-Eintrag-Historie: Treffer per Registrierung und/oder Blocked-Fingerabdruck, inkl. „zuletzt gesehen“ relativ formatiert (`just now` / `N min ago` / `N h ago` / `N days ago`) |

Jede Zeile aus `sightings` wird über `_decorate` um `exit_time_local`, `dwell_seconds` (Verweildauer zwischen Entry und Exit) und `aircraft_info_url` (Wikipedia-Suchlink auf Modell oder ICAO-Code) angereichert.

## Legacy-Import (`legacy_import.py`)

Einmalige, transaktionale Übernahme einer vorbestehenden ha-tinker-`sky_sightings.db` in die neue v1-Datenbank, ausgelöst über den Service `skywatch.import_legacy_db` (siehe [services.md](services.md)):

1. Die Quell-Datenbank wird per `ATTACH DATABASE … AS legacy` an die Ziel-Connection gehängt (rein lesend).
2. Für `sightings`, `entries` und `airport_movements` prüft `_copy_table`, ob alle **erforderlichen** Spalten in der Quelle existieren — fehlen welche, bricht der Import mit `LegacyImportError` ab, statt stillschweigend Daten zu verlieren. Optionale Spalten (`entry_time`, `heading`, `vertical_speed`) werden nur übernommen, wenn sie vorhanden sind.
3. Nach dem Kopieren läuft dieselbe „https:https://“-Foto-URL-Bereinigung wie in der Migration, aber gezielt auf die gerade importierten Zeilen.
4. Bei Erfolg wird committet und die Quell-DB wieder `DETACH`ed; bei jedem Fehler wird zurückgerollt und trotzdem detached, damit die Ziel-Connection sauber bleibt.
5. Der Service schreibt danach eine Sentinel-Datei `.legacy_imported` neben die neue DB.

Der Import ist **read-only auf der Quelle** und **transaktional auf dem Ziel** — es entsteht kein Zeilenverlust, und ein Fehlschlag hinterlässt die Ziel-DB unverändert.
