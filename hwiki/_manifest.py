from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from slugify import slugify  # python-slugify

MANIFEST_FILE = ".hwiki.json"


class ManifestEntry(TypedDict):
    title: str
    space: str
    version: int
    parent_id: str | None
    path: str          # relative filename, e.g. "477874699-kartochka.md"
    content_hash: str  # "sha256:<hex>"


class Manifest(TypedDict):
    host: str
    space: str
    root_id: str
    pulled_at: str     # ISO8601
    pages: dict[str, ManifestEntry]  # keyed by page_id (str)


def make_slug(title: str, max_length: int = 60) -> str:
    """Transliterate title to a lowercase kebab-case slug (max_length chars)."""
    return slugify(title, max_length=max_length, separator="-", lowercase=True)


def page_filename(page_id: str, title: str) -> str:
    """Return the canonical filename for a page: '{id}-{slug}.md'."""
    slug = make_slug(title)
    if slug:
        return f"{page_id}-{slug}.md"
    return f"{page_id}.md"


def content_hash(text: str) -> str:
    digest = hashlib.sha256(text.encode()).hexdigest()
    return f"sha256:{digest}"


def load_manifest(directory: Path) -> Manifest:
    path = directory / MANIFEST_FILE
    with open(path) as f:
        return json.load(f)


def save_manifest(directory: Path, manifest: Manifest) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / MANIFEST_FILE
    with open(path, "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def find_manifest_dir(start: Path) -> Path | None:
    """Walk up from start looking for .hwiki.json. Return the directory or None."""
    current = start.resolve()
    while True:
        if (current / MANIFEST_FILE).exists():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
