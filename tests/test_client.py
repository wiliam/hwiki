"""Tests for ConfluenceClient request shapes using respx."""
import pytest
import respx
import httpx
import json
from hwiki._http import HttpClient
from hwiki.client import ConfluenceClient

BASE = "https://test.example.com"

AC = "http://www.atlassian.com/schema/confluence/4/ac/"
RI = "http://www.atlassian.com/schema/confluence/4/ri/"

# A minimal page response dict
def _page_response(page_id="123", title="My Page", version=1, space_key="ENG"):
    return {
        "id": page_id,
        "title": title,
        "space": {"key": space_key},
        "version": {"number": version},
        "body": {
            "storage": {
                "value": "<p>Content</p>",
                "representation": "storage",
            }
        },
        "_links": {"base": BASE, "webui": f"/pages/{page_id}"},
    }


@pytest.fixture
def http():
    return HttpClient(base_url=BASE, token="tok", timeout=5, max_retries=0)


@pytest.fixture
def client(http):
    return ConfluenceClient(http)


# ---------------------------------------------------------------------------
# get_page
# ---------------------------------------------------------------------------

@respx.mock
def test_get_page(client):
    page_data = _page_response("123", "Test Page", version=5)
    respx.get(f"{BASE}/rest/api/content/123").mock(
        return_value=httpx.Response(200, json=page_data,
                                    headers={"Content-Type": "application/json"})
    )
    page = client.get_page("123")
    assert page["id"] == "123"
    assert page["title"] == "Test Page"
    assert page["space_key"] == "ENG"
    assert page["version"] == 5
    assert page["body_storage"] == "<p>Content</p>"


# ---------------------------------------------------------------------------
# search_pages
# ---------------------------------------------------------------------------

@respx.mock
def test_search_pages(client):
    search_data = {
        "results": [
            {
                "id": "101",
                "title": "Page One",
                "space": {"key": "ENG"},
                "_links": {"base": BASE, "webui": "/pages/101"},
            },
            {
                "id": "102",
                "title": "Page Two",
                "space": {"key": "ENG"},
                "_links": {"base": BASE, "webui": "/pages/102"},
            },
        ]
    }
    respx.get(f"{BASE}/rest/api/content/search").mock(
        return_value=httpx.Response(200, json=search_data,
                                    headers={"Content-Type": "application/json"})
    )
    results = client.search_pages("space = ENG")
    assert len(results) == 2
    assert results[0]["id"] == "101"
    assert results[0]["title"] == "Page One"
    assert results[1]["id"] == "102"


# ---------------------------------------------------------------------------
# create_page
# ---------------------------------------------------------------------------

@respx.mock
def test_create_page(client):
    # POST to create
    post_route = respx.post(f"{BASE}/rest/api/content").mock(
        return_value=httpx.Response(200, json={"id": "456"},
                                    headers={"Content-Type": "application/json"})
    )
    # GET to fetch the created page
    respx.get(f"{BASE}/rest/api/content/456").mock(
        return_value=httpx.Response(200, json=_page_response("456", "New Page", version=1),
                                    headers={"Content-Type": "application/json"})
    )
    page = client.create_page(
        space_key="ENG",
        title="New Page",
        storage_xhtml="<p>Hello</p>",
    )
    assert page["id"] == "456"
    assert page["title"] == "New Page"

    # Verify POST body structure
    assert post_route.called
    request = post_route.calls[0].request
    body = json.loads(request.content)
    assert body["type"] == "page"
    assert body["title"] == "New Page"
    assert body["space"]["key"] == "ENG"
    assert body["body"]["storage"]["value"] == "<p>Hello</p>"
    assert body["body"]["storage"]["representation"] == "storage"


# ---------------------------------------------------------------------------
# update_page
# ---------------------------------------------------------------------------

@respx.mock
def test_update_page(client):
    put_route = respx.put(f"{BASE}/rest/api/content/123").mock(
        return_value=httpx.Response(200, json={"id": "123"},
                                    headers={"Content-Type": "application/json"})
    )
    respx.get(f"{BASE}/rest/api/content/123").mock(
        return_value=httpx.Response(200, json=_page_response("123", "Updated Page", version=3),
                                    headers={"Content-Type": "application/json"})
    )
    page = client.update_page(
        "123",
        title="Updated Page",
        storage_xhtml="<p>Updated</p>",
        current_version=2,
    )
    assert page["title"] == "Updated Page"

    # Verify PUT body has version.number = current_version + 1
    assert put_route.called
    request = put_route.calls[0].request
    body = json.loads(request.content)
    assert body["version"]["number"] == 3  # 2 + 1
    assert body["title"] == "Updated Page"
    assert body["body"]["storage"]["value"] == "<p>Updated</p>"


# ---------------------------------------------------------------------------
# upload_attachment
# ---------------------------------------------------------------------------

@respx.mock
def test_upload_attachment(client, tmp_path):
    # Create a temp file to upload
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello attachment")

    attachment_response = {
        "results": [
            {
                "id": "att001",
                "title": "test.txt",
                "metadata": {"mediaType": "text/plain"},
                "_links": {"download": "/download/att001/test.txt"},
            }
        ]
    }
    post_route = respx.post(f"{BASE}/rest/api/content/123/child/attachment").mock(
        return_value=httpx.Response(200, json=attachment_response,
                                    headers={"Content-Type": "application/json"})
    )

    attachment = client.upload_attachment("123", test_file)
    assert attachment["id"] == "att001"
    assert attachment["filename"] == "test.txt"

    # Verify X-Atlassian-Token header was sent
    assert post_route.called
    request = post_route.calls[0].request
    assert request.headers.get("x-atlassian-token") == "no-check"
