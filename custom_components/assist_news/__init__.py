"""Set up the Assist News integration.

Related files: config_flow.py (publisher config entries), api.py (selectable LLM API).
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm

from .api import AssistNewsAPI

from .const import (
    CONF_ARTICLE_BODY_CHARS,
    CONF_BRIEFING_CHARS,
    CONF_NEWS_COUNT,
    CONF_PRESS_ID,
    DEFAULT_ARTICLE_BODY_CHARS,
    DEFAULT_BRIEFING_CHARS,
    DEFAULT_NEWS_COUNT,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a configured Naver publisher entry."""
    unregister_api = llm.async_register_api(hass, AssistNewsAPI(hass, entry))
    entry.async_on_unload(unregister_api)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a publisher entry."""
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entries and add article and briefing length defaults."""
    if entry.version < 5:
        data = dict(entry.data)
        if entry.version == 1:
            data.setdefault(CONF_PRESS_ID, "001")
            data.setdefault("press_name", "연합뉴스")
        data.setdefault(CONF_ARTICLE_BODY_CHARS, DEFAULT_ARTICLE_BODY_CHARS)
        data.setdefault(CONF_BRIEFING_CHARS, DEFAULT_BRIEFING_CHARS)
        data.setdefault(CONF_NEWS_COUNT, DEFAULT_NEWS_COUNT)
        update: dict[str, object] = {
            "data": data,
            "version": 5,
        }
        if entry.version == 1:
            update["title"] = data["press_name"]
            update["unique_id"] = entry.unique_id or data[CONF_PRESS_ID]
        hass.config_entries.async_update_entry(entry, **update)
    return True
