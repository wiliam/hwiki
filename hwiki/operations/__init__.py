import json
import sys
from pathlib import Path

import keyring

from .._http import HttpClient
from ..client import ConfluenceClient
from ..utils import KEYRING_SERVICE, CONFIG_PATH


class HwikiOperation:
    def __init__(self):
        self._client_instance = None
        self._verbose = False

    def configure_arg_parser(self, subparsers):
        raise NotImplementedError()

    def get_config(self) -> dict:
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"ERROR: config not found — create {CONFIG_PATH}", file=sys.stderr)
            sys.exit(2)

    def get_token(self) -> str:
        cfg = self.get_config()
        token = keyring.get_password(KEYRING_SERVICE, cfg["user"])
        if not token:
            print("ERROR: no token — run: hwiki login", file=sys.stderr)
            sys.exit(2)
        return token

    def client(self) -> ConfluenceClient:
        if self._client_instance is None:
            cfg = self.get_config()
            http = HttpClient(
                base_url=cfg["host"],
                token=self.get_token(),
                timeout=cfg.get("timeout", 20),
                verbose=self._verbose,
            )
            self._client_instance = ConfluenceClient(http)
        return self._client_instance
