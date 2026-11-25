"""Pairing flow: the TV shows a prompt, accept it with the remote."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

try:  # newer Home Assistant releases ship probatio in place of voluptuous
    import probatio as vol
except ImportError:  # pragma: no cover
    import voluptuous as vol

from aiowebostv import WebOsTvPairError

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import config_validation as cv

from .const import CONF_CLIENT_KEY, CONF_HOST, DOMAIN
from .tv import CONNECT_ERRORS, new_client

HOST_SCHEMA = vol.Schema({vol.Required(CONF_HOST): cv.string})


class LgtvPointerFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._host = ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._host = user_input[CONF_HOST]
            return await self.async_step_pairing()
        return self.async_show_form(step_id="user", data_schema=HOST_SCHEMA)

    async def async_step_pairing(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client = new_client(self.hass, self._host, None)
            try:
                await client.connect()
            except WebOsTvPairError:
                errors["base"] = "error_pairing"
            except CONNECT_ERRORS:
                errors["base"] = "cannot_connect"
            else:
                key = client.client_key
                uuid = client.tv_info.hello["deviceUUID"]
                model = client.tv_info.system.get("modelName", "")
                await client.disconnect()
                # Same unique id as the webostv entry of this TV: the services find us through it.
                await self.async_set_unique_id(uuid)
                self._abort_if_unique_id_configured({CONF_HOST: self._host})
                return self.async_create_entry(
                    title=f"LG {model} pointer".replace("  ", " "),
                    data={CONF_HOST: self._host, CONF_CLIENT_KEY: key},
                )
        return self.async_show_form(step_id="pairing", errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        self._host = entry_data[CONF_HOST]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client = new_client(self.hass, self._host, None)
            try:
                await client.connect()
            except WebOsTvPairError:
                errors["base"] = "error_pairing"
            except CONNECT_ERRORS:
                errors["base"] = "cannot_connect"
            else:
                key = client.client_key
                await client.disconnect()
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data={CONF_HOST: self._host, CONF_CLIENT_KEY: key}
                )
        return self.async_show_form(step_id="reauth_confirm", errors=errors)
