from __future__ import annotations
from typing import TypedDict


class Page(TypedDict):
    id: str
    title: str
    space_key: str
    version: int
    body_storage: str


class SearchHit(TypedDict):
    id: str
    title: str
    space_key: str
    url: str


class Attachment(TypedDict):
    id: str
    filename: str
    media_type: str
    download_url: str
