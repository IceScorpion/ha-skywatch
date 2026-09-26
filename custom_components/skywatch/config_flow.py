"""Config flow without OptionsFlow."""

from __future__ import annotations
import re

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
 
from .const import (
    CONF_AIRPORT_IATA,
    CONF_ALERTS_ENABLED,
    CONF_HELO_CODES,
    CONF_HOME_LATITUDE,
    CONF_HOME_LONGITUDE,
    CONF_MILITARY_CODES,
    CONF_OVERHEAD_ALTITUDE_FT,
    CONF_OVERHEAD_DISTANCE_KM,
    CONF_QUIET_HOURS_END,
    CONF_QUIET_HOURS_START,
    CONF_RADIUS_KM,
    CONF_SOURCE,
    CONF_WATCH_LIST,
    DEFAULT_HELO_CODES,
    DEFAULT_MILITARY_CODES,
    DEFAULT_OVERHEAD_ALTITUDE_FT,
    DEFAULT_OVERHEAD_DISTANCE_KM,
    DEFAULT_RADIUS_KM,
    DOMAIN,
    SOURCE_FR24,
)

FR24_DOMAIN = "flightradar24"
SINGLETON_UNIQUE_ID = "skywatch_singleton"

SLUG_RE = re.compile(r"^[a-z0-9_]+$")

class SkywatchConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    
    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> SkywatchOptionsFlowHandler:
        return SkywatchOptionsFlowHandler()


    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            lat = user_input.get(CONF_HOME_LATITUDE)
            lon = user_input.get(CONF_HOME_LONGITUDE)
            iata = (user_input.get(CONF_AIRPORT_IATA) or "").strip().upper()
            radius = user_input.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM)

            if lat is None or not -90 <= float(lat) <= 90:
                errors["base"] = "invalid_latitude"
            elif lon is None or not -180 <= float(lon) <= 180:
                errors["base"] = "invalid_longitude"
            elif iata and (len(iata) != 3 or not iata.isalpha()):
                errors["base"] = "invalid_iata"
            elif not self.hass.config_entries.async_entries(FR24_DOMAIN):
                errors["base"] = "fr24_not_loaded"

            if not errors:
                await self.async_set_unique_id(SINGLETON_UNIQUE_ID)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Skywatch",
                    data={
                        CONF_HOME_LATITUDE: float(lat),
                        CONF_HOME_LONGITUDE: float(lon),
                        CONF_AIRPORT_IATA: iata or None,
                        CONF_RADIUS_KM: int(radius),
                        CONF_SOURCE: SOURCE_FR24,
                    },
                )

        default_lat = self.hass.config.latitude
        default_lon = self.hass.config.longitude

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOME_LATITUDE, default=default_lat): vol.Coerce(float),
                    vol.Required(CONF_HOME_LONGITUDE, default=default_lon): vol.Coerce(float),
                    vol.Optional(CONF_AIRPORT_IATA, default=""): str,
                    vol.Required(CONF_RADIUS_KM, default=DEFAULT_RADIUS_KM): vol.Coerce(int),
                }
            ),
            errors=errors,
        )
        
def _parse_codes(raw: str) -> list[str]:
    """'a109, b06,c130' -> ['A109', 'B06', 'C130'] (dedupliziert, sortiert)."""
    return sorted({c.strip().upper() for c in raw.split(",") if c.strip()})
 
 
class SkywatchOptionsFlowHandler(OptionsFlow):
    """Options flow handler for Skywatch."""
 
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ):
        """Hauptmenü der Optionen."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["watch_list", "codes", "thresholds"],
        )
 
    # ------------------------------------------------------------------
    # Watch list
    # ------------------------------------------------------------------
 
    async def async_step_watch_list(
        self, user_input: dict[str, Any] | None = None
    ):
        """Untermenü: Watch-List-Einträge verwalten."""
        watch_list = list(self.config_entry.options.get(CONF_WATCH_LIST, []))
        menu_options = ["add_watch"]
        if watch_list:
            menu_options.append("remove_watch")
        menu_options.append("init")  # zurück zum Hauptmenü
 
        return self.async_show_menu(
            step_id="watch_list",
            menu_options=menu_options,
            description_placeholders={
                "current": ", ".join(w["slug"] for w in watch_list) or "(leer)",
            },
        )
 
    async def async_step_add_watch(
        self, user_input: dict[str, Any] | None = None
    ):
        """Neuen Watch-List-Eintrag anlegen."""
        errors: dict[str, str] = {}
        watch_list = list(self.config_entry.options.get(CONF_WATCH_LIST, []))
 
        if user_input is not None:
            slug = user_input["slug"].strip().lower()
            registration = (user_input.get("registration") or "").strip().upper()
            aircraft_code = (user_input.get("aircraft_code") or "").strip().upper()
            match_blocked = user_input.get("match_blocked", False)
 
            if not SLUG_RE.match(slug):
                errors["slug"] = "invalid_slug"
            elif any(w["slug"] == slug for w in watch_list):
                errors["slug"] = "slug_exists"
            elif not registration and not aircraft_code and not match_blocked:
                errors["base"] = "watch_entry_needs_criteria"
 
            if not errors:
                watch_list.append(
                    {
                        "slug": slug,
                        "label": user_input.get("label") or slug,
                        "registration": registration or None,
                        "aircraft_code": aircraft_code or None,
                        "match_blocked": match_blocked,
                    }
                )
                new_options = {
                    **self.config_entry.options,
                    CONF_WATCH_LIST: watch_list,
                }
                return self.async_create_entry(title="", data=new_options)
 
        return self.async_show_form(
            step_id="add_watch",
            data_schema=vol.Schema(
                {
                    vol.Required("slug"): str,
                    vol.Optional("label", default=""): str,
                    vol.Optional("registration", default=""): str,
                    vol.Optional("aircraft_code", default=""): str,
                    vol.Optional("match_blocked", default=False): bool,
                }
            ),
            errors=errors,
        )
 
    async def async_step_remove_watch(
        self, user_input: dict[str, Any] | None = None
    ):
        """Bestehenden Watch-List-Eintrag entfernen."""
        watch_list = list(self.config_entry.options.get(CONF_WATCH_LIST, []))
 
        if user_input is not None:
            slug_to_remove = user_input["slug"]
            watch_list = [w for w in watch_list if w["slug"] != slug_to_remove]
            new_options = {
                **self.config_entry.options,
                CONF_WATCH_LIST: watch_list,
            }
            return self.async_create_entry(title="", data=new_options)
 
        return self.async_show_form(
            step_id="remove_watch",
            data_schema=vol.Schema(
                {
                    vol.Required("slug"): vol.In(
                        {w["slug"]: f'{w["label"]} ({w["slug"]})' for w in watch_list}
                    ),
                }
            ),
        )
 
    # ------------------------------------------------------------------
    # ICAO code lists (Helicopter / Military)
    # ------------------------------------------------------------------
 
    async def async_step_codes(
        self, user_input: dict[str, Any] | None = None
    ):
        """Helicopter- und Military-ICAO-Codes bearbeiten."""
        current_helo = self.config_entry.options.get(
            CONF_HELO_CODES, list(DEFAULT_HELO_CODES)
        )
        current_military = self.config_entry.options.get(
            CONF_MILITARY_CODES, list(DEFAULT_MILITARY_CODES)
        )
 
        if user_input is not None:
            new_options = {
                **self.config_entry.options,
                CONF_HELO_CODES: _parse_codes(user_input.get("helo_codes", "")),
                CONF_MILITARY_CODES: _parse_codes(
                    user_input.get("military_codes", "")
                ),
            }
            return self.async_create_entry(title="", data=new_options)
 
        return self.async_show_form(
            step_id="codes",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "helo_codes", default=", ".join(current_helo)
                    ): str,
                    vol.Optional(
                        "military_codes", default=", ".join(current_military)
                    ): str,
                }
            ),
        )
 
    # ------------------------------------------------------------------
    # Overhead-Schwellenwerte, Alerts, Quiet Hours
    # ------------------------------------------------------------------
 
    async def async_step_thresholds(
        self, user_input: dict[str, Any] | None = None
    ):
        """Overhead-Distanz/Höhe, Alert-Schalter, Quiet Hours."""
        errors: dict[str, str] = {}
        opts = self.config_entry.options
 
        if user_input is not None:
            new_options = {
                **opts,
                CONF_OVERHEAD_DISTANCE_KM: user_input[CONF_OVERHEAD_DISTANCE_KM],
                CONF_OVERHEAD_ALTITUDE_FT: user_input[CONF_OVERHEAD_ALTITUDE_FT],
                CONF_ALERTS_ENABLED: user_input.get(CONF_ALERTS_ENABLED, True),
                CONF_QUIET_HOURS_START: user_input.get(CONF_QUIET_HOURS_START)
                or None,
                CONF_QUIET_HOURS_END: user_input.get(CONF_QUIET_HOURS_END)
                or None,
            }
            return self.async_create_entry(title="", data=new_options)
 
        return self.async_show_form(
            step_id="thresholds",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_OVERHEAD_DISTANCE_KM,
                        default=opts.get(
                            CONF_OVERHEAD_DISTANCE_KM, DEFAULT_OVERHEAD_DISTANCE_KM
                        ),
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_OVERHEAD_ALTITUDE_FT,
                        default=opts.get(
                            CONF_OVERHEAD_ALTITUDE_FT, DEFAULT_OVERHEAD_ALTITUDE_FT
                        ),
                    ): vol.Coerce(int),
                    vol.Optional(
                        CONF_ALERTS_ENABLED,
                        default=opts.get(CONF_ALERTS_ENABLED, True),
                    ): bool,
                    vol.Optional(
                        CONF_QUIET_HOURS_START,
                        default=opts.get(CONF_QUIET_HOURS_START, "") or "",
                    ): str,
                    vol.Optional(
                        CONF_QUIET_HOURS_END,
                        default=opts.get(CONF_QUIET_HOURS_END, "") or "",
                    ): str,
                }
            ),
            errors=errors,
        )        
