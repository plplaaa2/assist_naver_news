"""Search one configured publisher and summarize a selected result.

Related files: api.py (tool registration), news.py (article body extraction).
"""

from __future__ import annotations

import asyncio
from html import unescape
import logging
import re
from time import monotonic
from urllib.parse import urlencode
from uuid import uuid4

from aiohttp import ClientError, ClientTimeout
import probatio

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.llm import Tool, ToolAnnotations, ToolResult

from .const import DOMAIN
from .news import parse_article_body

_LOGGER = logging.getLogger(__name__)
_LINK = re.compile(r"https://n\.news\.naver\.com/(?:mnews/)?article/(\d+)/(\d+)")


def _owner(context):
    """Bind opaque search snapshots to the requesting user, device and agent."""
    return (
        getattr(context.context, "user_id", None),
        context.device_id,
        context.agent_id,
    )


async def _fetch(session, url):
    """Read a public Naver page with the same timeout as major news."""
    async with session.get(url, timeout=ClientTimeout(total=15)) as response:
        response.raise_for_status()
        return await response.text()


class SearchNewsTool(Tool):
    """Find up to three articles for one registered publisher."""

    integration = DOMAIN
    annotations = ToolAnnotations(read_only=True, destructive=False, idempotent=False)
    parameters = probatio.Schema({
        probatio.Required("query"): probatio.All(str, probatio.Length(min=1, max=200)),
    })

    def __init__(self, press_id, press_name, results):
        self.press_id = press_id
        self.press_name = press_name
        self.results = results
        self.name = f"{DOMAIN}__search_{press_id}_news"
        self.title = f"{press_name} 뉴스 검색"
        self.description = (
            f"Search news about a topic only from {press_name}. "
            "Read the returned numbered titles, publisher and dates, then ask which "
            "article the user wants summarized. Do not summarize or select an article "
            "until the user chooses. Keep search_id for the follow-up selection tool. "
            "Do not speak URLs or search_id. If multiple publisher tools are searched, "
            "present at most three results total and remember the exact search_id and "
            "article number behind each spoken choice."
        )

    async def async_call(self, hass, tool_input, llm_context):
        query = tool_input.tool_args["query"].strip()
        if not query:
            return ToolResult(data={"error": "검색어를 말씀해 주세요."}, error=True)
        # Expire snapshots and bound memory without replacing an active search.
        for key, value in list(self.results.items()):
            if value["expires"] <= monotonic():
                self.results.pop(key, None)
        url = "https://search.naver.com/search.naver?" + urlencode({
            "where": "news", "query": query, "mynews": "1", "office_type": "1",
            "news_office_checked": str(1000 + int(self.press_id)), "sort": "0",
        })
        session = async_get_clientsession(hass)
        try:
            html = await _fetch(session, url)
            links = list(dict.fromkeys(
                f"https://n.news.naver.com/mnews/article/{press}/{article}"
                for press, article in _LINK.findall(unescape(html))
                if press == self.press_id.zfill(3)
            ))[:6]
            async def metadata(link):
                try:
                    page = await _fetch(session, link)
                    title = re.search(
                        r'<meta\s+property="og:title"\s+content="([^"]+)"', page
                    )
                    date = re.search(r'data-date-time="([^"]+)"', page)
                    if title:
                        return {"title": unescape(title[1]), "url": link,
                                "time": date[1] if date else ""}
                except (ClientError, TimeoutError):
                    _LOGGER.warning("Unable to fetch search article metadata")
                return None
            articles = [item for item in await asyncio.gather(
                *(metadata(link) for link in links)
            ) if item][:3]
        except (ClientError, TimeoutError):
            _LOGGER.warning("Unable to search publisher %s", self.press_id)
            return ToolResult(data={"error": "뉴스 검색에 실패했습니다. 다시 요청해 주세요."},
                              error=True)
        search_id = uuid4().hex
        if len(self.results) >= 100:
            self.results.pop(next(iter(self.results)))
        self.results[search_id] = {
            "owner": _owner(llm_context), "expires": monotonic() + 1800,
            "articles": articles,
        }
        return ToolResult(data={
            "search_id": search_id, "publisher": self.press_name,
            "count": len(articles),
            "articles": [
                {"number": number, "title": item["title"], "time": item["time"]}
                for number, item in enumerate(articles, 1)
            ],
        })


class ReadSearchNewsTool(Tool):
    """Fetch a selected article from an immutable search snapshot."""

    integration = DOMAIN
    annotations = ToolAnnotations(read_only=True, destructive=False, idempotent=True)
    parameters = probatio.Schema({
        probatio.Required("search_id"): str,
        probatio.Required("number"): probatio.All(int, probatio.Range(min=1, max=3)),
    })

    def __init__(self, press_id, results):
        self.results = results
        self.name = f"{DOMAIN}__read_{press_id}_search_news"
        self.description = (
            "After the user selects a numbered news search result, fetch it using "
            "the exact search_id and original result number. Summarize its body in "
            "about 500 Korean characters using a calm news anchor style and the five "
            "Ws and one H. Omit facts absent from the body. Read the title first. "
            "Do not read the full article or URLs. If the snapshot is unavailable, "
            "ask the user to search again instead of guessing."
        )

    async def async_call(self, hass, tool_input, llm_context):
        snapshot = self.results.get(tool_input.tool_args["search_id"])
        number = tool_input.tool_args["number"]
        if (not snapshot or snapshot["expires"] <= monotonic()
                or snapshot["owner"] != _owner(llm_context)):
            return ToolResult(data={"error": "검색 목록이 만료됐습니다. 다시 검색해 주세요."},
                              error=True)
        if not 1 <= number <= len(snapshot["articles"]):
            return ToolResult(data={"error": "목록에 있는 기사 번호를 선택해 주세요."},
                              error=True)
        article = snapshot["articles"][number - 1]
        try:
            html = await _fetch(async_get_clientsession(hass), article["url"])
        except (ClientError, TimeoutError):
            return ToolResult(data={"error": "선택한 기사를 가져오지 못했습니다."}, error=True)
        body = parse_article_body(html, 10000)
        if not body:
            return ToolResult(data={"error": "선택한 기사의 본문을 찾지 못했습니다."},
                              error=True)
        return ToolResult(data={
            "title": article["title"], "time": article["time"], "body": body,
            "briefing_chars": 500,
        })
