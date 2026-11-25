"""The lgtv_pointer services. Callers name the webostv media_player; we find our own entry for that TV."""
from __future__ import annotations

from typing import Any

try:  # newer Home Assistant releases ship probatio in place of voluptuous
    import probatio as vol
except ImportError:  # pragma: no cover
    import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .icons import download_app_icons
from .tv import Tv

_BASE = {vol.Required("entity_id"): cv.entity_id}
_XY = {vol.Required("dx"): vol.Coerce(int), vol.Required("dy"): vol.Coerce(int)}
# down=1 keeps the pointer button pressed while moving (drag); down=0 releases it.
_MOVE = {**_XY, vol.Optional("down", default=0): vol.All(vol.Coerce(int), vol.In((0, 1)))}


def tv_for_entity(hass: HomeAssistant, entity_id: str) -> Tv:
    """Our Tv for the TV behind a webostv media_player (both entries share the TV's unique id)."""
    entity = er.async_get(hass).async_get(entity_id)
    source = hass.config_entries.async_get_entry(entity.config_entry_id) if entity else None
    if source is None or source.domain != "webostv":
        raise HomeAssistantError(f"{entity_id} is not a webostv entity")
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        if entry.unique_id == source.unique_id:
            return entry.runtime_data
    raise HomeAssistantError(f"Add the LG webOS TV pointer integration for {entity_id}")


def async_setup_services(hass: HomeAssistant) -> None:
    async def client(call: ServiceCall):
        return await tv_for_entity(hass, call.data["entity_id"]).connected()

    async def move(call: ServiceCall) -> None:
        data = call.data
        await (await client(call)).move(data["dx"], data["dy"], data["down"])

    async def click(call: ServiceCall) -> None:
        await (await client(call)).click()

    async def scroll(call: ServiceCall) -> None:
        data = call.data
        await (await client(call)).scroll(data["dx"], data["dy"])

    async def watch_keyboard(call: ServiceCall) -> None:
        await tv_for_entity(hass, call.data["entity_id"]).watch_keyboard(call.data["entity_id"])

    async def app_icons(call: ServiceCall) -> dict[str, Any]:
        return {"icons": await download_app_icons(hass, await client(call))}

    hass.services.async_register(DOMAIN, "move", move, vol.Schema({**_BASE, **_MOVE}))
    hass.services.async_register(DOMAIN, "click", click, vol.Schema(_BASE))
    hass.services.async_register(DOMAIN, "scroll", scroll, vol.Schema({**_BASE, **_XY}))
    hass.services.async_register(DOMAIN, "watch_keyboard", watch_keyboard, vol.Schema(_BASE))
    hass.services.async_register(
        DOMAIN, "app_icons", app_icons, vol.Schema(_BASE), supports_response=SupportsResponse.ONLY
    )
