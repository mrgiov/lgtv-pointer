from aiowebostv import WebOsTvPairError
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.lgtv_pointer.const import CONF_CLIENT_KEY, CONF_HOST, DOMAIN

from .conftest import HOST, UUID


async def _pair(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    assert result["step_id"] == "pairing"
    return await hass.config_entries.flow.async_configure(result["flow_id"], {})


async def test_pairing_creates_an_entry_with_the_tv_key(hass, client):
    result = await _pair(hass)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: HOST, CONF_CLIENT_KEY: "paired-key"}
    assert result["result"].unique_id == UUID  # the same id as the webostv entry of this TV
    client.disconnect.assert_awaited()


async def test_rejected_pairing_shows_an_error(hass, client):
    client.connect.side_effect = WebOsTvPairError("no")
    result = await _pair(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "error_pairing"}


async def test_unreachable_tv_shows_an_error(hass, client):
    client.connect.side_effect = TimeoutError
    result = await _pair(hass)
    assert result["errors"] == {"base": "cannot_connect"}


async def test_same_tv_cannot_be_added_twice(hass, client, entry):
    result = await _pair(hass)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
