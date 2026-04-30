import sys
from getpass import getpass

import keyring
import typer

from . import get_config
from .._http import HttpClient, HwikiHttpError
from ..client import ConfluenceClient
from ..utils import KEYRING_SERVICE

name = "login"
help_text = "Set Confluence Personal Access Token"


def run() -> None:
    cfg = get_config()
    user, host = cfg["user"], cfg["host"]
    token = getpass(f"Personal Access Token for {user}@{host}: ")
    keyring.set_password(KEYRING_SERVICE, user, token)
    http = HttpClient(base_url=host, token=token, timeout=cfg.get("timeout", 20))
    client = ConfluenceClient(http)
    try:
        me = client.whoami()
        print(f"logged in as {me.get('displayName', user)}")
    except HwikiHttpError as e:
        typer.echo(f"ERROR: login failed: {e.status_code} {e.body}", err=True)
        try:
            keyring.delete_password(KEYRING_SERVICE, user)
        except Exception:
            pass
        raise typer.Exit(3)
