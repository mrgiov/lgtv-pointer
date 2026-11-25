import asyncio
import re

import pytest
from aiowebostv import WebOsTvPairError
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMockResponse

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


async def test_refused_pairing_is_a_clear_error(hass, client, setup):
    client.connect.side_effect = WebOsTvPairError("refused")
    with pytest.raises(HomeAssistantError, match="remove and add"):
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


async def test_two_simultaneous_watch_calls_subscribe_once(hass, client, setup):
    async def slow_send(*args):
        await asyncio.sleep(0.01)  # a real send yields to the event loop

    client.command.side_effect = slow_send
    await asyncio.gather(call(hass, "watch_keyboard"), call(hass, "watch_keyboard"))
    client.create_subscription_handler.assert_awaited_once()


async def test_failed_subscription_can_be_retried(hass, client, setup):
    client.command.side_effect = [OSError("boom"), None]
    with pytest.raises(OSError):
        await call(hass, "watch_keyboard")
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


async def test_icon_files_do_not_pile_up_when_the_tv_changes_its_urls(hass, client, setup, tmp_path, aioclient_mock):
    hass.config.config_dir = str(tmp_path)
    aioclient_mock.get(re.compile(r"https://tv\.local/.*"), content=b"png")
    for boot in ("aaa", "bbb", "ccc"):  # three TV boots, each with new urls for the same apps
        client.request.return_value = {
            "launchPoints": [
                {"title": f"App {i}", "icon": f"https://tv.local/resources/{boot}/{i}.png"} for i in range(5)
            ]
        }
        result = await call(hass, "app_icons")
        assert len(result["icons"]) == 5
    assert len(list((tmp_path / "www/lg-tv-remote/icons").iterdir())) == 5


async def test_a_failed_download_keeps_the_icon_we_already_have(hass, client, setup, tmp_path, aioclient_mock):
    hass.config.config_dir = str(tmp_path)
    client.request.return_value = {"launchPoints": [{"title": "Netflix", "icon": "https://tv.local/n.png"}]}
    aioclient_mock.get("https://tv.local/n.png", content=b"png")
    first = await call(hass, "app_icons")
    aioclient_mock.clear_requests()
    aioclient_mock.get("https://tv.local/n.png", status=500)
    assert await call(hass, "app_icons") == first


async def test_app_icons_never_asks_the_tv_for_many_icons_at_once(hass, client, setup, tmp_path, aioclient_mock):
    hass.config.config_dir = str(tmp_path)
    client.request.return_value = {
        "launchPoints": [{"title": f"App {i}", "icon": f"https://tv.local/{i}.png"} for i in range(30)]
    }
    running = peak = 0

    async def slow_icon(method, url, data):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1
        return AiohttpClientMockResponse(method, url, response=b"png")

    aioclient_mock.get(re.compile(r"https://tv\.local/\d+\.png"), side_effect=slow_icon)
    result = await call(hass, "app_icons")
    assert len(result["icons"]) == 30
    assert peak <= 4


async def test_unload_disconnects(hass, client, setup):
    assert await hass.config_entries.async_unload(setup.entry_id)
    client.disconnect.assert_awaited()
