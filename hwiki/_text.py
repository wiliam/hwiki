from __future__ import annotations
import re
from urllib.parse import urlparse, parse_qs, unquote


def parse_page_id(value: str) -> str:
    """Accept a raw page ID or a Confluence webui URL, return the numeric page ID.

    Handles:
      - raw numeric ID
      - viewpage.action?pageId=N
      - /pages/N
    For /display/SPACE/Title URLs, returns the value unchanged — caller must
    use resolve_page_id() on the client to look up the ID via API.
    """
    if value.isdigit():
        return value
    parsed = urlparse(value)
    qs = parse_qs(parsed.query)
    if "pageId" in qs:
        return qs["pageId"][0]
    m = re.search(r"/pages/(\d+)", parsed.path)
    if m:
        return m.group(1)
    return value


def parse_display_url(value: str) -> tuple[str, str]:
    """Parse a /display/SPACE/Title URL into (space_key, decoded_title).

    Returns ("", "") if the URL doesn't match the display format.
    """
    parsed = urlparse(value)
    m = re.match(r"/display/([^/]+)/(.+)", parsed.path)
    if m:
        space_key = m.group(1)
        title = unquote(m.group(2))
        return space_key, title
    return "", ""
