"""Shared fixtures: a fake aiowebostv client, so no TV is ever touched."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lgtv_pointer.const import CONF_CLIENT_KEY, CONF_HOST, DOMAIN

UUID = "tv-uuid-1"
HOST = "192.0.2.10"


@pytest.fixture(autouse=True)
def enable_custom_integrations(enable_custom_integrations):
    return enable_custom_integrations


@pytest.fixture
def client():
    """The fake client; patched into every place that builds a WebOsClient."""
    fake = MagicMock()
    fake.client_key = "paired-key"
    fake.command_count = 0
    fake.connection = object()
    fake.tv_info.hello = {"deviceUUID": UUID}
    fake.tv_info.system = {"modelName": "OLED65C34LA"}
    for name in ("connect", "disconnect", "move", "click", "scroll", "command", "create_subscription_handler"):
        setattr(fake, name, AsyncMock())
    fake.request = AsyncMock(return_value={"launchPoints": []})
    with patch("custom_components.lgtv_pointer.tv.WebOsClient", return_value=fake):
        yield fake


@pytest.fixture
def entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=UUID, data={CONF_HOST: HOST, CONF_CLIENT_KEY: "paired-key"}
    )
    entry.add_to_hass(hass)
    return entry
