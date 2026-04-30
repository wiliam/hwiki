"""Tests for HttpClient retry behavior using respx."""
import pytest
import respx
import httpx
from hwiki._http import HttpClient, HwikiHttpError

BASE = "https://test.example.com"


@pytest.fixture
def client():
    return HttpClient(base_url=BASE, token="tok", timeout=5, max_retries=3)


# ---------------------------------------------------------------------------
# 429 with Retry-After numeric header — retries and succeeds
# ---------------------------------------------------------------------------

@respx.mock
def test_429_retries_then_succeeds(client, monkeypatch):
    monkeypatch.setattr("hwiki._http.time.sleep", lambda s: None)
    route = respx.get(f"{BASE}/rest/api/test")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "0"}, json={}),
        httpx.Response(200, json={"ok": True}, headers={"Content-Type": "application/json"}),
    ]
    result = client.get("rest/api/test")
    assert result == {"ok": True}
    assert route.call_count == 2


# ---------------------------------------------------------------------------
# 503 exhausted — raises HwikiHttpError after max retries
# ---------------------------------------------------------------------------

@respx.mock
def test_503_exhausted(client, monkeypatch):
    monkeypatch.setattr("hwiki._http.time.sleep", lambda s: None)
    route = respx.get(f"{BASE}/rest/api/test")
    route.side_effect = [
        httpx.Response(503, text="Service Unavailable"),
        httpx.Response(503, text="Service Unavailable"),
        httpx.Response(503, text="Service Unavailable"),
        httpx.Response(503, text="Service Unavailable"),
    ]
    with pytest.raises(HwikiHttpError) as exc_info:
        client.get("rest/api/test")
    assert exc_info.value.status_code == 503
    assert route.call_count == 4  # 1 initial + 3 retries


# ---------------------------------------------------------------------------
# 401 — not retried, raises immediately
# ---------------------------------------------------------------------------

@respx.mock
def test_401_no_retry(client, monkeypatch):
    monkeypatch.setattr("hwiki._http.time.sleep", lambda s: None)
    route = respx.get(f"{BASE}/rest/api/test")
    route.return_value = httpx.Response(401, text="Unauthorized")
    with pytest.raises(HwikiHttpError) as exc_info:
        client.get("rest/api/test")
    assert exc_info.value.status_code == 401
    assert route.call_count == 1


# ---------------------------------------------------------------------------
# Transport error then success
# ---------------------------------------------------------------------------

@respx.mock
def test_transport_error_then_success(client, monkeypatch):
    monkeypatch.setattr("hwiki._http.time.sleep", lambda s: None)
    route = respx.get(f"{BASE}/rest/api/test")
    route.side_effect = [
        httpx.ConnectError("conn failed"),
        httpx.Response(200, json={"id": "1"}, headers={"Content-Type": "application/json"}),
    ]
    result = client.get("rest/api/test")
    assert result == {"id": "1"}
    assert route.call_count == 2


# ---------------------------------------------------------------------------
# 200 JSON response — returns dict
# ---------------------------------------------------------------------------

@respx.mock
def test_200_json_response(client):
    respx.get(f"{BASE}/rest/api/content/42").mock(
        return_value=httpx.Response(
            200,
            json={"id": "42", "title": "My Page"},
            headers={"Content-Type": "application/json"},
        )
    )
    result = client.get("rest/api/content/42")
    assert isinstance(result, dict)
    assert result["id"] == "42"
    assert result["title"] == "My Page"
