"""Register one selectable Home Assistant LLM API per Naver publisher.

Related files: __init__.py (API lifecycle), news.py (HTML parsing),
config_flow.py (per-publisher settings).
"""

from __future__ import annotations

import asyncio
import logging

from aiohttp import ClientError, ClientTimeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.llm import (
    API,
    APIInstance,
    LLMContext,
    Tool,
    ToolAnnotations,
    ToolInput,
    ToolResult,
)

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
from .news import parse_article_body, parse_major_news

_LOGGER = logging.getLogger(__name__)


class AssistNewsAPI(API):
    """An independently selectable LLM API for one configured publisher."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize this publisher's API."""
        self.entry = entry
        press_id = entry.data[CONF_PRESS_ID]
        press_name = entry.data.get("press_name", f"언론사 {press_id}")
        super().__init__(
            hass=hass,
            id=f"{DOMAIN}_{press_id}",
            name=f"{press_name} 뉴스",
        )

    async def async_get_api_instance(self, llm_context: LLMContext) -> APIInstance:
        """Return this publisher's news tool and briefing guidance."""
        press_id = self.entry.data[CONF_PRESS_ID]
        press_name = self.entry.data.get("press_name", f"언론사 {press_id}")
        body_chars = self.entry.options.get(
            CONF_ARTICLE_BODY_CHARS,
            self.entry.data.get(
                CONF_ARTICLE_BODY_CHARS,
                DEFAULT_ARTICLE_BODY_CHARS,
            ),
        )
        briefing_chars = self.entry.options.get(
            CONF_BRIEFING_CHARS,
            self.entry.data.get(CONF_BRIEFING_CHARS, DEFAULT_BRIEFING_CHARS),
        )
        news_count = self.entry.options.get(
            CONF_NEWS_COUNT,
            self.entry.data.get(CONF_NEWS_COUNT, DEFAULT_NEWS_COUNT),
        )
        return APIInstance(
            api=self,
            api_prompt="This tool provides news.",
            llm_context=llm_context,
            tools=[
                GetMajorNewsTool(
                    press_id, press_name, news_count, body_chars, briefing_chars
                )
            ],
        )


class GetMajorNewsTool(Tool):
    """Fetch headlines and article bodies from one Naver publisher."""

    integration = DOMAIN
    annotations = ToolAnnotations(read_only=True, destructive=False, idempotent=True)

    def __init__(
        self,
        press_id: str,
        press_name: str,
        news_count: int,
        body_chars: int,
        briefing_chars: int,
    ) -> None:
        """Initialize a tool for one publisher."""
        self.press_id = press_id
        self.press_name = press_name
        self.news_count = news_count
        self.body_chars = body_chars
        self.briefing_chars = briefing_chars
        self.name = f"{DOMAIN}__get_{press_id}_major_news"
        self.title = f"{press_name} 주요 뉴스"
        # Guide complete briefs using the five Ws and one H. Related: README.md, README.ko.md.
        self.description = (
            f"Fetch up to {news_count} major news articles from Naver {press_name}. "
            f"Each article includes its original title, time, and body (up to {body_chars:,} characters). "
            "Check the returned count and articles list before composing the briefing. "
            "Unless the user explicitly requests a smaller number or a filtered selection, "
            "brief every returned article exactly once in the order provided. "
            "Do not interpret 'major news' as permission to select only a subset. "
            "If the user specifies a number, brief that many articles, or all available "
            "articles if fewer were returned, preserving their order. "
            "Keep each summary concise so that all required articles are covered, "
            "and check that none were accidentally omitted before finishing. "
            "Use each title exactly as provided; do not paraphrase or edit it. "
            f"Summarize only the body in about {briefing_chars:,} Korean characters or fewer. "
            "For each briefing, cover who, what, when, where, why, and how "
            "as stated in the article body. Combine the facts into natural sentences. "
            "Omit any element missing from the body, and prioritize the most important "
            "facts when the length limit is tight. "
            "By default, deliver spoken briefings like a calm, neutral news anchor. "
            "Use short sentences and formal polite endings in Korean. "
            "When reading multiple articles, use brief natural transitions such as "
            "'첫 소식입니다' and '이어서 다음 소식입니다' where appropriate. "
            "Follow the user's requested delivery style if specified. "
            "Provide article links only when explicitly requested. "
            "Respond in the user's language; use Korean when the user asks in Korean."
        )

    async def async_call(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> ToolResult:
        """Fetch the configured number of headlines and their article bodies."""
        url = NEWS_URL.format(press_id=self.press_id)
        session = async_get_clientsession(hass)
        try:
            async with session.get(
                url,
                headers={"User-Agent": "Home Assistant Assist News/0.1"},
                timeout=ClientTimeout(total=15),
            ) as response:
                response.raise_for_status()
                html = await response.text()
        except (ClientError, TimeoutError) as err:
            _LOGGER.warning(
                "Unable to fetch Naver publisher %s headlines: %s", self.press_id, err
            )
            return ToolResult(data={"error": "뉴스 페이지를 가져오지 못했습니다."}, error=True)

        articles = parse_major_news(html, self.news_count, url)
        if not articles:
            _LOGGER.warning("No major news articles were found at %s", url)
            return ToolResult(data={"error": "뉴스 페이지에서 기사를 찾지 못했습니다."}, error=True)

        semaphore = asyncio.Semaphore(3)

        async def fetch_body(article: dict[str, str]) -> dict[str, str]:
            """Fetch one article body while limiting parallel requests."""
            async with semaphore:
                try:
                    async with session.get(
                        article["url"],
                        headers={"User-Agent": "Home Assistant Assist News/0.1"},
                        timeout=ClientTimeout(total=15),
                    ) as response:
                        response.raise_for_status()
                        article_html = await response.text()
                except (ClientError, TimeoutError) as err:
                    _LOGGER.warning(
                        "Unable to fetch article body from %s: %s", article["url"], err
                    )
                    return {**article, "body": ""}
                return {
                    **article,
                    "body": parse_article_body(article_html, self.body_chars),
                }

        articles = await asyncio.gather(*(fetch_body(article) for article in articles))
        return ToolResult(
            data={
                "publisher": self.press_name,
                "source": url,
                "count": len(articles),
                "briefing_chars": self.briefing_chars,
                "articles": articles,
            }
        )
