from __future__ import annotations
import re
from urllib.parse import urlparse, parse_qs


def parse_page_id(value: str) -> str:
    """Accept a raw page ID or a Confluence webui URL, return the numeric page ID."""
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
