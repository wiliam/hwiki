import json

import keyring
import typer

from .._http import HttpClient
from ..client import ConfluenceClient
from ..utils import KEYRING_SERVICE, CONFIG_PATH

_verbose: bool = False
_config: dict | None = None
_client: ConfluenceClient | None = None


def set_verbose(v: bool) -> None:
    global _verbose
    _verbose = v


def get_config() -> dict:
    global _config
    if _config is None:
        try:
            _config = json.loads(CONFIG_PATH.read_text())
        except FileNotFoundError:
            typer.echo(f"ERROR: config not found — create {CONFIG_PATH}", err=True)
            raise typer.Exit(2)
    return _config


def get_token() -> str:
    cfg = get_config()
    token = keyring.get_password(KEYRING_SERVICE, cfg["user"])
    if not token:
        typer.echo("ERROR: no token — run: hwiki login", err=True)
        raise typer.Exit(2)
    return token


def get_client() -> ConfluenceClient:
    global _client
    if _client is None:
        cfg = get_config()
        http = HttpClient(
            base_url=cfg["host"],
            token=get_token(),
            timeout=cfg.get("timeout", 20),
            verbose=_verbose,
        )
        _client = ConfluenceClient(http)
    return _client
