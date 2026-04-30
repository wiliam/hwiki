from __future__ import annotations
from pathlib import Path

from ._http import HttpClient
from ._types import Page, SearchHit, Attachment
from ._text import parse_page_id, parse_display_url


class ConfluenceClient:
    def __init__(self, http: HttpClient):
        self._http = http

    def resolve_page_id(self, value: str) -> str:
        """Resolve any page reference (ID, viewpage URL, or display URL) to a numeric ID."""
        pid = parse_page_id(value)
        if pid.isdigit():
            return pid
        space_key, title = parse_display_url(value)
        if space_key and title:
            data = self._http.get("rest/api/content", params={
                "title": title,
                "spaceKey": space_key,
                "type": "page",
                "limit": 1,
            })
            results = data.get("results", [])
            if results:
                return results[0]["id"]
        return pid

    def whoami(self) -> dict:
        return self._http.get("rest/api/user/current")

    def get_page(self, page_id: str) -> Page:
        data = self._http.get(
            f"rest/api/content/{page_id}",
            params={"expand": "body.storage,version,space"},
        )
        return _parse_page(data)

    def search_pages(self, cql: str, limit: int = 25) -> list[SearchHit]:
        data = self._http.get(
            "rest/api/content/search",
            params={"cql": cql, "limit": limit, "expand": "space"},
        )
        return [_parse_search_hit(r) for r in data.get("results", [])]

    def create_page(self, *, space_key: str, title: str, storage_xhtml: str,
                    parent_id: str | None = None) -> Page:
        body: dict = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {"storage": {"value": storage_xhtml, "representation": "storage"}},
        }
        if parent_id:
            body["ancestors"] = [{"id": parent_id}]
        data = self._http.post("rest/api/content", json=body)
        return self.get_page(data["id"])

    def update_page(self, page_id: str, *, title: str, storage_xhtml: str,
                    current_version: int) -> Page:
        body = {
            "type": "page",
            "title": title,
            "version": {"number": current_version + 1},
            "body": {"storage": {"value": storage_xhtml, "representation": "storage"}},
        }
        self._http.put(f"rest/api/content/{page_id}", json=body)
        return self.get_page(page_id)

    def upload_attachment(self, page_id: str, file_path: Path,
                          comment: str | None = None) -> Attachment:
        params = {"comment": comment} if comment else None
        with open(file_path, "rb") as f:
            data = self._http.post(
                f"rest/api/content/{page_id}/child/attachment",
                params=params,
                files={"file": (file_path.name, f, "application/octet-stream")},
                headers={"X-Atlassian-Token": "no-check"},
            )
        result = data["results"][0]
        return Attachment(
            id=result["id"],
            filename=result["title"],
            media_type=result.get("metadata", {}).get("mediaType", ""),
            download_url=result["_links"]["download"],
        )

    def get_children(self, page_id: str, limit: int = 50) -> list[Page]:
        """Fetch direct child pages (metadata only, no body)."""
        data = self._http.get(
            f"rest/api/content/{page_id}/child/page",
            params={"expand": "version,space", "limit": limit},
        )
        return [_parse_page(r) for r in data.get("results", [])]

    def get_attachment_content(self, download_url: str) -> bytes:
        """Download raw attachment bytes. download_url is relative (from Attachment.download_url)."""
        return self._http.get(download_url.lstrip("/"))


def _parse_page(data: dict) -> Page:
    return Page(
        id=data["id"],
        title=data["title"],
        space_key=data.get("space", {}).get("key", ""),
        version=data.get("version", {}).get("number", 0),
        body_storage=data.get("body", {}).get("storage", {}).get("value", ""),
    )


def _parse_search_hit(data: dict) -> SearchHit:
    links = data.get("_links", {})
    base = links.get("base", "")
    webui = links.get("webui", "")
    return SearchHit(
        id=data["id"],
        title=data["title"],
        space_key=data.get("space", {}).get("key", ""),
        url=f"{base}{webui}" if base else webui,
    )
