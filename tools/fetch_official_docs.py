"""Fetches and caches plain-text content from docs.databricks.com pages.

Stdlib only (`urllib.request` + `html.parser`) — no `requests`/`beautifulsoup4`.
Validated against a real docs.databricks.com page: server-rendered HTML,
no JS required, `<main>` holds the article body.
"""
from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib import error, request

DEFAULT_CACHE_DIR = Path("data/docs_cache")


class _MainTextExtractor(HTMLParser):
    """Collects text inside <main> (falls back to the whole doc if no <main> is found)."""

    def __init__(self) -> None:
        super().__init__()
        self._in_main = False
        self._saw_main = False
        self._skip_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "main":
            self._in_main = True
            self._saw_main = True
        if tag in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "main":
            self._in_main = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._saw_main and not self._in_main:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)

    def get_text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._chunks)).strip()


def slugify_url(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    tail = re.sub(r"[^a-zA-Z0-9]+", "-", url.rstrip("/").rsplit("/", 2)[-1]).strip("-")
    return f"{tail or 'page'}-{digest}"


def fetch_html(url: str, timeout: int = 20) -> str | None:
    try:
        req = request.Request(url, headers={"User-Agent": "agent-databricks-tutor/0.1"})
        with request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except (error.HTTPError, error.URLError, TimeoutError, ValueError):
        return None


def html_to_text(html: str) -> str:
    parser = _MainTextExtractor()
    parser.feed(html)
    return parser.get_text()


def get_doc_text(url: str, cache_dir: Path = DEFAULT_CACHE_DIR, force: bool = False) -> str | None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify_url(url)
    text_path = cache_dir / f"{slug}.txt"
    html_path = cache_dir / f"{slug}.html"

    if text_path.exists() and not force:
        return text_path.read_text(encoding="utf-8")

    html = fetch_html(url)
    if html is None:
        return None

    html_path.write_text(html, encoding="utf-8")
    text = html_to_text(html)
    text_path.write_text(text, encoding="utf-8")
    return text
