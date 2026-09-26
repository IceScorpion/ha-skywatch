# Skywatch – Feature-Dokumentation

Diese Dokumentation beschreibt die Features der Home-Assistant-Integration **Skywatch**, so wie sie sich aus dem aktuellen Code unter `custom_components/skywatch/` ergeben (Stand: Branch `feature/uebernahme-ha-changes`, Version `0.2.0` laut `manifest.json`).

Skywatch erfasst Flugzeugsichtungen rund um einen konfigurierten Standort, persistiert sie in SQLite, klassifiziert sie (Hubschrauber / Militär / Watchlist) und stellt sie über Home-Assistant-Entities, Events, Services und eine Live-Karte zur Verfügung.

## Inhalt

| Dokument | Thema |
|---|---|
| [architektur.md](architektur.md) | Gesamtarchitektur: Backend-Adapter, Coordinator, Storage, Plattformen |
| [konfiguration.md](konfiguration.md) | Config Flow (Ersteinrichtung) und Options Flow (Watchlist, ICAO-Codes, Schwellwerte) |
| [entities.md](entities.md) | Alle Sensoren, Binary Sensors und Steuer-Entities im Detail |
| [klassifizierung.md](klassifizierung.md) | Hubschrauber-/Militär-Erkennung und Watchlist-Matching |
| [datenhaltung.md](datenhaltung.md) | SQLite-Schema, Abfragen, Migrationen, Legacy-Import |
| [events-und-blueprints.md](events-und-blueprints.md) | `skywatch_sighting`-Event und die drei mitgelieferten Automations-Blueprints |
| [live-karte.md](live-karte.md) | Live-Karte (`/api/skywatch/map`) und GeoJSON-Endpunkt |
| [services.md](services.md) | Aufrufbare Home-Assistant-Services (`skywatch.*`) |

## Kurzüberblick – was die Integration liefert

- **15 Sensor-Entities** für Tages-/Wochen-/Gesamtzählungen, Aktivität der letzten 1 h/24 h, Suchergebnisse, Stunden-Histogramm, Top-Routen, Overhead-, Militär-, Hubschrauber- und Flugzeugsichtungen, Flughafenbewegungen sowie aktuell im Gebiet befindliche Flugzeuge.
- **Pro-Watchlist-Sensor** – jeder konfigurierte Watch-Eintrag erzeugt automatisch `sensor.skywatch_watch_<slug>`.
- **2 Binary Sensors** – `binary_sensor.skywatch_has_aircraft` (Flugzeug im Radius) und `binary_sensor.skywatch_helicopter_overhead`.
- **4 native Steuer-Entities** – `number.skywatch_sightings_page`, `text.skywatch_search_term`, `switch.skywatch_alerts_enabled`, `button.skywatch_clear_search`.
- **Backend-agnostische Quellenanbindung** – aktuell ein Adapter für die Flightradar24-HACS-Integration; weitere Quellen (dump1090, tar1090, ADSB-Hub …) lassen sich als zusätzliche `Source`-Implementierung ergänzen, ohne Storage/Coordinator/Plattformen anzufassen.
- **Live-Karte** unter `/api/skywatch/map` (Leaflet + ArcGIS-Dark-Gray-Basemap) mit Flugzeug-Silhouetten, Höhen-Farbverlauf, Kurs-Rotation, 30-Minuten-Trails sowie AOI- und Hörweiten-Kreisen.
- **SQLite-Persistenz** unter `<config>/skywatch/sightings.db` mit versionierten Migrationen und vollindizierten Abfragen.
- **Einmaliger Legacy-Import** (`skywatch.import_legacy_db`) für eine vorbestehende `sky_sightings.db` aus dem ha-tinker-Setup.
- **3 Automatisierungs-Blueprints** – Einflug-Alarm, Watchlist-Treffer-Alarm, Tages-Digest.
- **Config Flow + mehrstufiger Options Flow** – Grundkonfiguration bei der Einrichtung, danach Watchlist-Pflege, ICAO-Code-Listen und Schwellwerte/Quiet-Hours über ein Menü.
