# LG webOS TV pointer

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

1. HACS → ⋮ → Custom repositories → add this repository, category **Integration**, then install it.
2. Enable it with one line in your configuration (for example a file in `packages/`):

   ```yaml
   lgtv_pointer:
   ```

3. Restart Home Assistant.

## Caveat

It reuses the WebSocket client that `webostv` has already opened (`entry.runtime_data.client`), which is an
internal detail of that integration. A Home Assistant update that changes it can break this component;
if the services stop working after an update, please open an issue.
