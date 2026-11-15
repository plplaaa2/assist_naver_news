"""Configuration flow for Assist News.

Related files: const.py (entry data key), api.py (per-press Assist APIs).
"""

from __future__ import annotations

import re
from html import unescape

from aiohttp import ClientError, ClientTimeout
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .const import (
    CONF_ARTICLE_BODY_CHARS,
    CONF_BRIEFING_CHARS,
    CONF_NEWS_COUNT,
    CONF_PRESS_ID,
    DEFAULT_ARTICLE_BODY_CHARS,
    DEFAULT_BRIEFING_CHARS,
    DEFAULT_NEWS_COUNT,
    DOMAIN,
    NEWS_URL,
)


class AssistNewsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Add multiple Naver news publishers, identified by their press IDs."""

    VERSION = 5

    async def async_step_user(self, user_input: dict[str, str | int] | None = None):
        """Add a Naver news publisher by its press ID."""
        errors: dict[str, str] = {}
        if user_input is not None:
            press_id = user_input[CONF_PRESS_ID].strip()
            if not re.fullmatch(r"\d{1,6}", press_id):
                errors[CONF_PRESS_ID] = "invalid_press_id"
            else:
                await self.async_set_unique_id(press_id)
                self._abort_if_unique_id_configured()
                url = NEWS_URL.format(press_id=press_id)
                session = async_get_clientsession(self.hass)
                try:
                    async with session.get(
                        url,
                        headers={"User-Agent": "Home Assistant Assist News/0.1"},
                        timeout=ClientTimeout(total=15),
                    ) as response:
                        response.raise_for_status()
                        html = await response.text()
                except (ClientError, TimeoutError):
                    errors["base"] = "cannot_connect"
                else:
                    press_name = _extract_press_name(html)
                    if press_name is None:
                        errors[CONF_PRESS_ID] = "invalid_press_id"
                    else:
                        return self.async_create_entry(
                            title=press_name,
                            data={
                                CONF_PRESS_ID: press_id,
                                "press_name": press_name,
                                CONF_ARTICLE_BODY_CHARS: user_input.get(
                                    CONF_ARTICLE_BODY_CHARS,
                                    DEFAULT_ARTICLE_BODY_CHARS,
                                ),
                                CONF_BRIEFING_CHARS: user_input.get(
                                    CONF_BRIEFING_CHARS,
                                    DEFAULT_BRIEFING_CHARS,
                                ),
                                CONF_NEWS_COUNT: user_input.get(
                                    CONF_NEWS_COUNT,
                                    DEFAULT_NEWS_COUNT,
                                ),
                            },
                        )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PRESS_ID): str,
                    vol.Optional(
                        CONF_ARTICLE_BODY_CHARS,
                        default=DEFAULT_ARTICLE_BODY_CHARS,
                    ): vol.All(int, vol.Range(min=100, max=10000)),
                    vol.Optional(
                        CONF_BRIEFING_CHARS,
                        default=DEFAULT_BRIEFING_CHARS,
                    ): vol.All(int, vol.Range(min=30, max=500)),
                    vol.Optional(
                        CONF_NEWS_COUNT,
                        default=DEFAULT_NEWS_COUNT,
                    ): vol.All(int, vol.Range(min=1, max=30)),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return options flow to adjust news and text lengths."""
        return AssistNewsOptionsFlow()


class AssistNewsOptionsFlow(config_entries.OptionsFlow):
    """Allow changing news count and text lengths for a publisher."""

    async def async_step_init(self, user_input: dict[str, int] | None = None):
        """Set article count, body length, and briefing length."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ARTICLE_BODY_CHARS,
                        default=self.config_entry.options.get(
                            CONF_ARTICLE_BODY_CHARS,
                            self.config_entry.data.get(
                                CONF_ARTICLE_BODY_CHARS,
                                DEFAULT_ARTICLE_BODY_CHARS,
                            ),
                        ),
                    ): vol.All(int, vol.Range(min=100, max=10000)),
                    vol.Required(
                        CONF_BRIEFING_CHARS,
                        default=self.config_entry.options.get(
                            CONF_BRIEFING_CHARS,
                            self.config_entry.data.get(
                                CONF_BRIEFING_CHARS,
                                DEFAULT_BRIEFING_CHARS,
                            ),
                        ),
                    ): vol.All(int, vol.Range(min=30, max=500)),
                    vol.Required(
                        CONF_NEWS_COUNT,
                        default=self.config_entry.options.get(
                            CONF_NEWS_COUNT,
                            self.config_entry.data.get(
                                CONF_NEWS_COUNT,
                                DEFAULT_NEWS_COUNT,
                            ),
                        ),
                    ): vol.All(int, vol.Range(min=1, max=30)),
                }
            ),
        )


def _extract_press_name(html: str) -> str | None:
    """Extract the publisher name from the Naver press header."""
    match = re.search(
        r'<a[^>]*class="[^"]*press_hd_name_link[^"]*"[^>]*>(.*?)</a>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    name = unescape(re.sub(r"<[^>]+>", " ", match.group(1)))
    name = " ".join(name.split())
    return name or None
