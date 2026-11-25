# LG webOS TV pointer

**English** · [Italiano](README.it.md)

Home Assistant custom integration that adds to the core `webostv` integration what it leaves out.
It is the companion of [lg-tv-remote-card](https://github.com/mrgiov/lg-tv-remote-card), but the
services can be used on their own.

| Service | What it does |
| --- | --- |
| `lgtv_pointer.move` (`dx`, `dy`) | moves the magic-remote pointer |
| `lgtv_pointer.click` | clicks at the pointer |
| `lgtv_pointer.scroll` (`dx`, `dy`) | scrolls |
| `lgtv_pointer.watch_keyboard` | fires the `lgtv_pointer_keyboard` event when a text field gains or loses focus on the TV |
| `lgtv_pointer.app_icons` | copies the TV's app icons to `/config/www/lg-tv-remote/icons/` and returns `{icons: {title: url}}` (the TV serves them over HTTPS with a self-signed certificate, so a browser cannot load them directly) |

All services take `entity_id` of a `webostv` media player.

## Install

1. HACS → search for **LG webOS TV pointer** (or ⋮ → Custom repositories → this repository, category **Integration**), then install it.
2. Restart Home Assistant.
3. Turn the TV on. Settings → Devices & services → Add integration → **LG webOS TV pointer**, enter the TV's IP address, select Submit and accept the connection request on the TV.

Services take the `entity_id` of the TV's `webostv` media player; the integration finds its own entry for that TV.

## How it connects

It pairs with the TV itself and keeps its own connection, separate from the core `webostv` integration (the TV lists it as a second paired app). It connects when a service is called, so a TV that is off is not a problem: the call then fails with "TV not connected".

## Upgrading from 1.x

1.x was switched on with a `lgtv_pointer:` line in your configuration and borrowed the connection of `webostv`. Remove that line (for example `packages/lgtv_pointer.yaml`), restart, and add the integration as above. The services and the `lgtv_pointer_keyboard` event are unchanged, so the card keeps working.
