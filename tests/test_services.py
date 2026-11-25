import pytest
from aiowebostv import WebOsTvPairError
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lgtv_pointer.const import DOMAIN, EVENT_KEYBOARD, IME_REGISTER_KEYBOARD

from .conftest import UUID

ENTITY = "media_player.lg_tv"


@pytest.fixture
async def setup(hass, client, entry):
    """Our entry plus a webostv entry (same TV) owning ENTITY."""
    webostv = MockConfigEntry(domain="webostv", unique_id=UUID)
    webostv.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "media_player", "webostv", UUID, config_entry=webostv, suggested_object_id="lg_tv"
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def call(hass, service, **data):
    return await hass.services.async_call(
        DOMAIN, service, {"entity_id": ENTITY, **data}, blocking=True, return_response=service == "app_icons"
    )


async def test_move_click_scroll_use_our_own_connection(hass, client, setup):
    await call(hass, "move", dx=3, dy=-4)
    client.move.assert_awaited_with(3, -4, 0)
    await call(hass, "move", dx=1, dy=1, down=1)
    client.move.assert_awaited_with(1, 1, 1)
    await call(hass, "click")
    client.click.assert_awaited_once()
    await call(hass, "scroll", dx=0, dy=9)
    client.scroll.assert_awaited_with(0, 9)
    client.connect.assert_awaited()


async def test_setup_does_not_connect(hass, client, setup):
    client.connect.assert_not_awaited()  # the TV is usually off


async def test_unreachable_tv_is_a_clear_error(hass, client, setup):
    client.connect.side_effect = TimeoutError
    with pytest.raises(HomeAssistantError, match="TV not connected"):
        await call(hass, "click")


async def test_lost_pairing_starts_reauth(hass, client, setup):
    client.connect.side_effect = WebOsTvPairError("revoked")
    with pytest.raises(ConfigEntryAuthFailed):
        await call(hass, "click")


async def test_tv_without_our_entry_says_what_to_add(hass, client, entry):
    """Another TV has our entry loaded, this one does not: it must not borrow the other connection."""
    webostv = MockConfigEntry(domain="webostv", unique_id="other-tv")
    webostv.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "media_player", "webostv", "other-tv", config_entry=webostv, suggested_object_id="lg_tv"
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    with pytest.raises(HomeAssistantError, match="Add the LG webOS TV pointer"):
        await call(hass, "click")


async def test_keyboard_watch_subscribes_once_per_connection_and_fires_events(hass, client, setup):
    events = []
    hass.bus.async_listen(EVENT_KEYBOARD, events.append)

    await call(hass, "watch_keyboard")
    await call(hass, "watch_keyboard")  # same connection: no second subscription
    client.command.assert_awaited_once_with("subscribe", IME_REGISTER_KEYBOARD, {"subscribe": True}, 0)

    on_state = client.create_subscription_handler.await_args.args[2]
    await on_state({"currentWidget": {"focus": True, "contentType": "url"}})
    await on_state({"currentWidget": None})  # ignored
    await hass.async_block_till_done()
    assert [e.data for e in events] == [{"entity_id": ENTITY, "focus": True, "content_type": "url"}]

    client.connection = object()  # the TV reconnected: subscriptions are gone
    await call(hass, "watch_keyboard")
    assert client.command.await_count == 2


async def test_app_icons_returns_local_urls(hass, client, setup, tmp_path, aioclient_mock):
    hass.config.config_dir = str(tmp_path)
    client.request.return_value = {
        "launchPoints": [
            {"title": "Netflix", "largeIcon": "https://tv.local/netflix.png"},
            {"title": "Broken", "icon": "https://tv.local/broken.png"},
            {"title": "NoIcon"},
        ]
    }
    aioclient_mock.get("https://tv.local/netflix.png", content=b"png")
    aioclient_mock.get("https://tv.local/broken.png", status=500)
    result = await call(hass, "app_icons")
    assert list(result["icons"]) == ["Netflix"]
    assert result["icons"]["Netflix"].startswith("/local/lg-tv-remote/icons/")


async def test_unload_disconnects(hass, client, setup):
    assert await hass.config_entries.async_unload(setup.entry_id)
    client.disconnect.assert_awaited()
