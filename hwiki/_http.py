from __future__ import annotations
import sys
import time
import random
from email.utils import parsedate_to_datetime
from datetime import timezone

import httpx


class HwikiHttpError(Exception):
    def __init__(self, status_code: int, body: str, method: str, url: str):
        self.status_code = status_code
        self.body = body
        self.method = method
        self.url = url
        super().__init__(f"HTTP {status_code} {method} {url}")


class _BearerAuth(httpx.Auth):
    def __init__(self, token: str):
        self._token = token

    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request


_RETRYABLE = {429, 502, 503, 504}


class HttpClient:
    def __init__(self, base_url: str, token: str, timeout: int = 20,
                 max_retries: int = 3, verbose: bool = False):
        self._verbose = verbose
        self._max_retries = max_retries
        self._client = httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            auth=_BearerAuth(token),
            timeout=timeout,
        )

    def request(self, method: str, path: str, *, params=None, json=None,
                files=None, headers=None) -> dict | bytes:
        path = path.lstrip("/")
        attempt = 0
        delay = 0.5
        while True:
            try:
                resp = self._client.request(
                    method, path, params=params, json=json,
                    files=files, headers=headers or {},
                )
            except httpx.TransportError as exc:
                attempt += 1
                if attempt > self._max_retries:
                    raise HwikiHttpError(0, str(exc), method, path) from exc
                self._log(f"{method} {path} → transport error, retry {attempt}")
                time.sleep(self._backoff(delay))
                delay *= 2
                continue

            if self._verbose:
                self._log(f"{method} {path} → {resp.status_code}")

            if resp.status_code in _RETRYABLE:
                attempt += 1
                if attempt > self._max_retries:
                    raise HwikiHttpError(resp.status_code, resp.text[:2048], method, path)
                wait = self._retry_after(resp, delay)
                self._log(f"{method} {path} → {resp.status_code}, retry {attempt} in {wait:.1f}s")
                time.sleep(wait)
                delay *= 2
                continue

            if resp.is_error:
                body = resp.text[:2048]
                if self._verbose:
                    self._log(f"  response: {body}")
                raise HwikiHttpError(resp.status_code, body, method, path)

            ct = resp.headers.get("content-type", "")
            return resp.json() if "json" in ct else resp.content

    def get(self, path, **kw): return self.request("GET", path, **kw)
    def post(self, path, **kw): return self.request("POST", path, **kw)
    def put(self, path, **kw): return self.request("PUT", path, **kw)
    def delete(self, path, **kw): return self.request("DELETE", path, **kw)

    def close(self):
        self._client.close()

    def _log(self, msg: str):
        print(msg, file=sys.stderr)

    @staticmethod
    def _backoff(delay: float) -> float:
        return min(delay * random.uniform(0.8, 1.2), 60.0)

    @staticmethod
    def _retry_after(resp: httpx.Response, default_delay: float) -> float:
        header = resp.headers.get("retry-after")
        if header:
            if header.isdigit():
                return min(float(header), 60.0)
            try:
                dt = parsedate_to_datetime(header)
                from datetime import datetime
                wait = (dt - datetime.now(tz=timezone.utc)).total_seconds()
                return max(0, min(wait, 60.0))
            except Exception:
                pass
        jitter = random.uniform(0.8, 1.2)
        return min(default_delay * jitter, 60.0)
