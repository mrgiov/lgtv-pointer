"""One TV: our own aiowebostv connection, opened on demand and kept for later calls."""
from __future__ import annotations

import logging
from typing import Any

from aiowebostv import WebOsClient, WebOsTvCommandError, WebOsTvPairError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_CLIENT_KEY, CONF_HOST, EVENT_KEYBOARD, IME_REGISTER_KEYBOARD

_LOGGER = logging.getLogger(__name__)

CONNECT_ERRORS = (OSError, TimeoutError, WebOsTvCommandError)


def new_client(hass: HomeAssistant, host: str, key: str | None) -> WebOsClient:
    return WebOsClient(host, key, client_session=async_get_clientsession(hass))


class Tv:
    """The connection that belongs to one config entry (the TV is usually off, so connect lazily)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self.client = new_client(hass, entry.data[CONF_HOST], entry.data[CONF_CLIENT_KEY])
        # The connection the keyboard subscription was made on: aiowebostv drops its subscriptions
        # on every reconnect, so a different connection object means "subscribe again".
        self._keyboard_connection: Any = None

    async def connected(self) -> WebOsClient:
        """Return the client, connecting first when needed."""
        try:
            await self.client.connect()
        except WebOsTvPairError as err:
            raise HomeAssistantError("The TV refused the pairing: remove and add the integration again") from err
        except CONNECT_ERRORS as err:
            raise HomeAssistantError("TV not connected") from err
        return self.client

    async def disconnect(self) -> None:
        await self.client.disconnect()

    async def watch_keyboard(self, entity_id: str) -> None:
        """Fire `lgtv_pointer_keyboard` whenever a text field gains or loses focus (idempotent per connection)."""
        client = await self.connected()
        if self._keyboard_connection is client.connection:
            return
        # Claim the connection before the first await below, so a second call cannot subscribe twice.
        self._keyboard_connection = client.connection

        async def on_keyboard_state(payload: dict[str, Any] | None) -> None:
            _LOGGER.debug("IME payload for %s: %s", entity_id, payload)
            widget = (payload or {}).get("currentWidget")
            if widget is None:
                return
            self._hass.bus.async_fire(
                EVENT_KEYBOARD,
                {
                    "entity_id": entity_id,
                    "focus": bool(widget.get("focus")),
                    "content_type": widget.get("contentType"),
                },
            )

        # client.subscribe() waits for a first reply, but the TV only answers once a text field has
        # focus. Register the handler and send the request ourselves, without waiting.
        # shortcut: uses aiowebostv's command_count and create_subscription_handler, which are not
        # documented; if a release changes them, switch to client.subscribe() in a background task.
        try:
            uid = client.command_count
            client.command_count += 1
            await client.create_subscription_handler(IME_REGISTER_KEYBOARD, uid, on_keyboard_state)
            await client.command("subscribe", IME_REGISTER_KEYBOARD, {"subscribe": True}, uid)
        except Exception:
            self._keyboard_connection = None  # let the next call try again
            raise
