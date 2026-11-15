"""Parse the latest major news from Naver's Yonhap News press page.

Related files: const.py (source URL and result limit), api.py (Assist tool).
"""

from __future__ import annotations

from html.parser import HTMLParser
from html import unescape
import re
import unicodedata
from urllib.parse import urljoin, urlparse

from .const import DEFAULT_NEWS_COUNT

_ARTICLE_CLASSES = {"press_news_link", "press_edit_news_link", "p_link"}
_TIME_PATTERN = re.compile(r"(?:\d{1,2}:\d{2}|\d+분전|\d+시간전|\d+일전|\d{1,2}월\s*\d{1,2}일\s*\d{1,2}:\d{2})$")
_BODY_TAGS_TO_SKIP = {"script", "style", "iframe", "figure", "button"}
_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
_ZERO_WIDTH_TRANSLATION = str.maketrans("", "", "\u200b\u200c\u200d\u2060\ufeff")


def _clean_news_text(text: str) -> str:
    """Decode entities and remove control, format, and decorative characters."""
    text = unescape(text).translate(_ZERO_WIDTH_TRANSLATION)
    cleaned: list[str] = []
    for character in text:
        category = unicodedata.category(character)
        if category in {"Cc", "Cf", "Cs", "Co", "Cn"}:
            continue
        if category == "So":
            continue
        cleaned.append(character)
    return " ".join("".join(cleaned).split())


class _NewsHTMLParser(HTMLParser):
    """Collect visible article links from the press page."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.items: list[dict[str, str]] = []
        self._anchor: dict[str, str] | None = None
        self._anchor_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a":
            self._anchor_depth += 1
            classes = set((attributes.get("class") or "").split())
            href = attributes.get("href") or ""
            parsed = urlparse(urljoin(self.base_url, href))
            if classes & _ARTICLE_CLASSES and parsed.hostname in {
                "n.news.naver.com",
                "news.naver.com",
            }:
                self._anchor = {"url": parsed.geturl(), "title": "", "time": ""}
        elif self._anchor is not None and tag in {"span", "em"}:
            if "time" in (attributes.get("class") or "").split():
                self._anchor["time"] = ""

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._anchor_depth == 0:
            return
        self._anchor_depth -= 1
        if self._anchor_depth == 0 and self._anchor is not None:
            title = _clean_news_text(self._anchor["title"])
            if title and all(item["url"] != self._anchor["url"] for item in self.items):
                match = _TIME_PATTERN.search(title)
                if match:
                    self._anchor["time"] = match.group(0)
                    title = title[: match.start()].rstrip()
                self._anchor["title"] = title
                self.items.append(self._anchor)
            self._anchor = None

    def handle_data(self, data: str) -> None:
        if self._anchor is not None:
            self._anchor["title"] += data


def parse_major_news(
    html: str,
    limit: int = DEFAULT_NEWS_COUNT,
    base_url: str = "https://media.naver.com/press/001",
) -> list[dict[str, str]]:
    """Return up to ``limit`` unique article titles, links, and displayed times."""
    parser = _NewsHTMLParser(base_url)
    parser.feed(html)
    return parser.items[: max(0, limit)]


class _ArticleBodyParser(HTMLParser):
    """Extract readable text from Naver's article body container."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._body_depth = 0
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if self._body_depth == 0:
            if tag == "article" and attributes.get("id") == "dic_area":
                self._body_depth = 1
            return

        classes = set((attributes.get("class") or "").split())
        if self._skip_depth:
            if tag not in _VOID_TAGS:
                self._skip_depth += 1
            return
        if tag in _BODY_TAGS_TO_SKIP or classes & {"end_photo_org", "img_desc"}:
            self._skip_depth += 1
            return
        if tag in {"br", "p", "div", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._body_depth == 0:
            return
        if self._skip_depth:
            if tag not in _VOID_TAGS:
                self._skip_depth -= 1
            return
        if tag == "article":
            self._body_depth = 0
        elif tag in {"p", "div", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._body_depth and not self._skip_depth:
            self.parts.append(data)


def parse_article_body(html: str, limit: int) -> str:
    """Return the readable article body, trimmed to ``limit`` characters."""
    parser = _ArticleBodyParser()
    parser.feed(html)
    text = _clean_news_text(" ".join(parser.parts))
    return text[: max(0, limit)]
