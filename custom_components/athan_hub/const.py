"""Constants for the Athan Hub integration."""

DOMAIN = "athan_hub"
DEFAULT_URL = "http://athan.local"
CONF_ATHAN_URL = "athan_url"

# Server key -> display name. "Shuruq" matches the Mawaqit integration.
PRAYERS = {
    "fajr": "Fajr",
    "shurooq": "Shuruq",
    "dhuhr": "Dhuhr",
    "asr": "Asr",
    "maghrib": "Maghrib",
    "isha": "Isha",
}
DAYS_AHEAD = 7
