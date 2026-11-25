"""Copies the TV's app icons next to Home Assistant so a browser can load them."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from aiowebostv import WebOsClient

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import ICONS_DIR, ICONS_URL, LIST_LAUNCH_POINTS

_LOGGER = logging.getLogger(__name__)


async def download_app_icons(hass: HomeAssistant, client: WebOsClient) -> dict[str, str]:
    """Download each app icon once and return {app title: local url}."""
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
