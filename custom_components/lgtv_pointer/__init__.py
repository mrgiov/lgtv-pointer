"""Expose parts of the webOS input stack that the core webostv integration leaves out.

The core integration keeps an aiowebostv client with an open input socket but only exposes
remote buttons. This adds:
  * lgtv_pointer.move / click / scroll   the magic-remote pointer
  * lgtv_pointer.watch_keyboard          starts listening to the TV's text field focus and
                                         fires `lgtv_pointer_keyboard` events on change
  * lgtv_pointer.app_icons               copies the TV's app icons into /config/www so a browser can
                                         load them (the TV serves them over HTTPS with its own certificate)
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType

DOMAIN = "lgtv_pointer"
EVENT_KEYBOARD = f"{DOMAIN}_keyboard"
IME_REGISTER_KEYBOARD = "com.webos.service.ime/registerRemoteKeyboard"
LIST_LAUNCH_POINTS = "com.webos.applicationManager/listLaunchPoints"
ICONS_DIR = "www/lg-tv-remote/icons"
ICONS_URL = "/local/lg-tv-remote/icons"

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

_BASE = {vol.Required("entity_id"): cv.entity_id}
_XY = {
    vol.Required("dx"): vol.Coerce(int),
    vol.Required("dy"): vol.Coerce(int),
}
# down=1 keeps the pointer button pressed while moving (drag); down=0 releases it.
_MOVE = {**_XY, vol.Optional("down", default=0): vol.All(vol.Coerce(int), vol.In((0, 1)))}

# entity_id -> websocket the keyboard subscription was made on. aiowebostv drops its
# subscriptions on every reconnect, so a different connection object means "subscribe again".
_keyboard_watches: dict[str, Any] = {}


def _client(hass: HomeAssistant, entity_id: str):
    """Return the connected aiowebostv client behind a webostv media_player entity."""
    entity = er.async_get(hass).async_get(entity_id)
    entry_id = entity.config_entry_id if entity else None
    entry = hass.config_entries.async_get_entry(entry_id) if entry_id else None
    if entry is None or entry.domain != "webostv":
        raise HomeAssistantError(f"{entity_id} is not a webostv entity")
    client = getattr(getattr(entry, "runtime_data", None), "client", None)
    if client is None or getattr(client, "input_connection", None) is None:
        raise HomeAssistantError("TV not connected")
    return client


async def _watch_keyboard(hass: HomeAssistant, entity_id: str) -> None:
    """Subscribe to the TV's text field focus (idempotent per connection)."""
    client = _client(hass, entity_id)
    if _keyboard_watches.get(entity_id) is client.connection:
        return

    async def on_keyboard_state(payload: dict[str, Any] | None) -> None:
        _LOGGER.debug("IME payload for %s: %s", entity_id, payload)
        widget = (payload or {}).get("currentWidget")
        if widget is None:
            return
        hass.bus.async_fire(
            EVENT_KEYBOARD,
            {
                "entity_id": entity_id,
                "focus": bool(widget.get("focus")),
                "content_type": widget.get("contentType"),
            },
        )

    # client.subscribe() waits for a first reply, but the TV only answers once a text field has
    # focus. Register the handler and send the request ourselves, without waiting.
    uid = client.command_count
    client.command_count += 1
    await client.create_subscription_handler(IME_REGISTER_KEYBOARD, uid, on_keyboard_state)
    await client.command("subscribe", IME_REGISTER_KEYBOARD, {"subscribe": True}, uid)
    _keyboard_watches[entity_id] = client.connection


async def _app_icons(hass: HomeAssistant, entity_id: str) -> dict[str, str]:
    """Download the app icons once and return {app title: local url}."""
    client = _client(hass, entity_id)
    response = await client.request(LIST_LAUNCH_POINTS)
    directory = Path(hass.config.path(ICONS_DIR))
    await hass.async_add_executor_job(lambda: directory.mkdir(parents=True, exist_ok=True))
    session = async_get_clientsession(hass, verify_ssl=False)  # the TV's certificate is self-signed

    icons: dict[str, str] = {}
    for launch_point in response.get("launchPoints", []):
        title = launch_point.get("title")
        source = launch_point.get("largeIcon") or launch_point.get("icon")
        if not title or not source or not source.startswith("http") or title in icons:
            continue
        name = f"{hashlib.sha1(source.encode()).hexdigest()[:16]}.png"
        target = directory / name
        if not await hass.async_add_executor_job(target.exists):
            try:
                async with session.get(source, timeout=10) as reply:
                    reply.raise_for_status()
                    data = await reply.read()
            except Exception as err:  # one broken icon must not stop the others
                _LOGGER.debug("Icon for %s not downloaded: %s", title, err)
                continue
            await hass.async_add_executor_job(target.write_bytes, data)
        icons[title] = f"{ICONS_URL}/{name}"
    return icons


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def move(call: ServiceCall) -> None:
        data = call.data
        await _client(hass, data["entity_id"]).move(data["dx"], data["dy"], data["down"])

    async def click(call: ServiceCall) -> None:
        await _client(hass, call.data["entity_id"]).click()

    async def scroll(call: ServiceCall) -> None:
        data = call.data
        await _client(hass, data["entity_id"]).scroll(data["dx"], data["dy"])

    async def watch_keyboard(call: ServiceCall) -> None:
        await _watch_keyboard(hass, call.data["entity_id"])

    async def app_icons(call: ServiceCall) -> dict[str, Any]:
        return {"icons": await _app_icons(hass, call.data["entity_id"])}

    hass.services.async_register(DOMAIN, "move", move, vol.Schema({**_BASE, **_MOVE}))
    hass.services.async_register(DOMAIN, "click", click, vol.Schema(_BASE))
    hass.services.async_register(DOMAIN, "scroll", scroll, vol.Schema({**_BASE, **_XY}))
    hass.services.async_register(DOMAIN, "watch_keyboard", watch_keyboard, vol.Schema(_BASE))
    hass.services.async_register(
        DOMAIN, "app_icons", app_icons, vol.Schema(_BASE), supports_response=SupportsResponse.ONLY,
    )
    return True
