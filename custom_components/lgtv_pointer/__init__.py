"""Pointer, scroll, keyboard focus events and app icons for LG webOS TVs.

Complements the core webostv integration with its own pairing and its own connection to the TV:
  * lgtv_pointer.move / click / scroll   the magic-remote pointer
  * lgtv_pointer.watch_keyboard          fires `lgtv_pointer_keyboard` events when a text field gains or loses focus
  * lgtv_pointer.app_icons               copies the TV's app icons into /config/www so a browser can load them
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .services import async_setup_services
from .tv import Tv

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

LgtvPointerEntry = ConfigEntry[Tv]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: LgtvPointerEntry) -> bool:
    # No connection here: the TV is usually off, the services connect when they are called.
    entry.runtime_data = Tv(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LgtvPointerEntry) -> bool:
    await entry.runtime_data.disconnect()
    return True
