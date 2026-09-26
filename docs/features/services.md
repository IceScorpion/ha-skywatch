# Services

Registriert in `services.py`, einmalig beim ersten Config Entry (`async_register_services`), entfernt beim letzten Unload (`async_unregister_services`). Alle Services sind unter der Domain `skywatch` erreichbar (Entwicklerwerkzeuge → Dienste bzw. YAML-Automatisierungen).

## `skywatch.import_legacy_db`

Migriert eine bestehende ha-tinker-`sky_sightings.db` verlustfrei in die neue Skywatch-Datenbank (siehe [datenhaltung.md](datenhaltung.md#legacy-import-legacy_importpy)).

| Feld | Typ | Default |
|---|---|---|
| `source_path` | string, optional | `/config/sky_sightings.db` |

Ablauf: öffnet die Ziel-DB in einem Executor-Thread, ruft `legacy_import.import_legacy_db` auf, committet bei Erfolg, rollt bei `LegacyImportError` zurück (und übersetzt den Fehler in ein `HomeAssistantError`, damit er im UI sichtbar wird) und schreibt abschließend eine Sentinel-Datei `.legacy_imported` neben die Ziel-DB.

Voraussetzung: mindestens ein Skywatch-Config-Entry muss existieren, sonst `HomeAssistantError("Skywatch is not configured.")`.

## `skywatch.set_page`

Setzt die Pagination-Seite für die „Recent sightings“-Liste — programmatisches Äquivalent zu `number.skywatch_sightings_page`.

| Feld | Typ | Validierung |
|---|---|---|
| `page` | int, Pflicht | ≥ 1 |

Wird auf **alle** vorhandenen Skywatch-Config-Entries angewendet (`coordinator.async_set_page`), löst einen sofortigen Refresh aus.

## `skywatch.set_search_term`

Setzt den Suchbegriff für `sensor.skywatch_log_search` — programmatisches Äquivalent zu `text.skywatch_search_term`.

| Feld | Typ |
|---|---|
| `term` | string, Pflicht |

Ebenfalls auf alle Config-Entries angewendet (`coordinator.async_set_search_term`).

---

Hinweis: `set_page` und `set_search_term` existieren zusätzlich zu den nativen `number`-/`text`-Entities, damit dieselbe Funktionalität sowohl per UI-Steuerung als auch direkt aus Automatisierungen/Skripten heraus ansprechbar ist.
