"""Constants for the LG webOS TV pointer integration."""

DOMAIN = "lgtv_pointer"
CONF_HOST = "host"
CONF_CLIENT_KEY = "client_key"

EVENT_KEYBOARD = f"{DOMAIN}_keyboard"
IME_REGISTER_KEYBOARD = "com.webos.service.ime/registerRemoteKeyboard"
LIST_LAUNCH_POINTS = "com.webos.applicationManager/listLaunchPoints"

ICONS_DIR = "www/lg-tv-remote/icons"
ICONS_URL = "/local/lg-tv-remote/icons"
