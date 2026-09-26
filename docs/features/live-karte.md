# Live-Karte

Zwei zusammengehörige HTTP-Endpunkte (`http.py`), beide `requires_auth = False`, damit sie sich problemlos in ein Lovelace-iframe einbetten lassen (iframes senden das HA-Auth-Cookie nicht mit).

## `GET /api/skywatch/flights.geojson`

Liefert eine GeoJSON-`FeatureCollection` der **aktuell** im Beobachtungsradius befindlichen Flugzeuge, aufgebaut aus `Source.current_flights()` des aktiven Backends (bei FR24: `sensor.flightradar24_current_in_area`).

- Jedes Flugzeug wird als `Point`-Feature ausgegeben, mit Eigenschaften `flight_id`, `callsign`, `altitude_ft`, `heading`, `ground_speed_kt`, `aircraft_code`, `aircraft_model`, sowie den serverseitig berechneten Klassifizierungen `is_helo`, `is_military`, `watch_slug`, `watch_label` (siehe [klassifizierung.md](klassifizierung.md)).
- Zusätzlich wird für jedes Flugzeug mit ≥2 erfassten Positionspunkten ein `LineString`-Feature mit den letzten **30 Minuten** an Positionsdaten angehängt (`coord.async_fetch_trails`, gespeist aus der `flight_positions`-Tabelle, siehe [datenhaltung.md](datenhaltung.md)) — das ergibt die „Schweif“-Linie hinter jedem Marker.
- Die Antwort trägt zusätzlich `home` (Koordinaten des konfigurierten Standorts), `radius_m` (konfigurierter Beobachtungsradius in Metern) und `audible_radius_m` (fest 8000 m = 8 km „Hörweite“).
- Ohne konfigurierten Config Entry liefert der Endpunkt eine leere FeatureCollection statt eines Fehlers.

## `GET /api/skywatch/map`

Liefert die statische HTML-Seite aus `custom_components/skywatch/www/skywatch-map.html` — bewusst **innerhalb** des Integrationspakets abgelegt, damit HACS die Datei zusammen mit dem Python-Code mitverteilt (ein Pfad unter `<repo_root>/www/` würde von HACS nicht mitgespiegelt).

Die Seite ist ein eigenständiges Leaflet-Setup (Leaflet 1.9.4 von unpkg, keine weiteren Build-Schritte) mit folgenden Merkmalen:

- **Basemap**: ArcGIS „World Dark Gray Base“ Kachel-Layer (`server.arcgisonline.com/.../Canvas/World_Dark_Gray_Base/`).
- **Polling**: Holt alle 5 s (`REFRESH_MS`) das GeoJSON und aktualisiert Marker, Trails und Kreise.
- **5 Flugzeug-Silhouetten** (inline SVG, `fill="currentColor"`, damit CSS die Farbe steuert): `jet`, `turboprop`, `light_ga` (leichte GA-Flugzeuge), `military`, `helo`.
  - Kategorisierung serverseitig vorgegeben für `is_military`/`is_helo`/`watch_slug`; für die Feinunterscheidung `turboprop` vs. `light_ga` vs. `jet` pflegt die Seite selbst zwei clientseitige ICAO-Code-Listen (`TURBOPROP_CODES`, `LIGHT_GA_CODES`).
  - Priorität der Kategorie: Watchlist-Treffer > Militär > Hubschrauber > Turboprop > Light GA > Jet.
- **5-stufiger Höhen-Farbverlauf** für alle Nicht-Sonderkategorien: `<10.000 ft` Rot, `10–20 Tsd. ft` Orange, `20–30 Tsd. ft` Gelb, `30–40 Tsd. ft` Hellblau, `>40 Tsd. ft` Dunkelblau. Hubschrauber sind immer bernsteinfarben, Watchlist-Treffer immer lila.
- **Kurs-Rotation**: Marker werden entsprechend `heading` gedreht (Nase zeigt in Flugrichtung).
- **Trail-Polylinien**: 30-Minuten-Schweif je Flugzeug, Farbe folgt der Flugzeug-Kategorie.
- **Kreise um den Heimatstandort**: der konfigurierte Beobachtungsradius (`radius_m`) sowie ein fester 8-km-„Hörweite“-Kreis (`audible_radius_m`).
- **Info-Panel unterhalb der Karte** (kein Hover-Tooltip mehr über der Karte — siehe Git-Historie „move hover display below map“): zeigt Callsign (verlinkt zu FlightAware), Modell/ICAO-Code, Flugfläche (`FL` = Höhe/100), Geschwindigkeit in Knoten, Kompasskurs, Entfernung vom Heimatstandort (Haversine-Berechnung im Client) und – falls zutreffend – das Watchlist-Label.
- **Freundliche Namen für bekannte Hubschrauber-Kennungen** (`HELI_NAMES`): eine kleine, clientseitig gepflegte Zuordnungstabelle von bereinigter Kennung/Callsign auf einen Klarnamen (z. B. Rettungshubschrauber-Rufnamen), analog zu einer serverseitigen `sensor.skywatch_heli_names`-Idee — muss bei Änderungen an beiden Stellen gepflegt werden, bis ein eigener JSON-Endpunkt das ablöst.
- **Legende** mit Silhouetten- und Farberklärung wird beim Laden aus denselben SVG-Definitionen generiert.

Selbst-Hoster, die kein CDN erreichen wollen, können die Skript-/Stylesheet-URLs direkt in der HTML-Datei austauschen — es gibt keine sonstigen externen Abhängigkeiten.
