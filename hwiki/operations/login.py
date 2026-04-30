import sys
from getpass import getpass

import keyring

from . import HwikiOperation
from .._http import HttpClient, HwikiHttpError
from ..client import ConfluenceClient
from ..utils import KEYRING_SERVICE


class Operation(HwikiOperation):
    def configure_arg_parser(self, subparsers):
        p = subparsers.add_parser("login", help="set Confluence Personal Access Token")
        p.set_defaults(func=self._run, op=self)

    def _run(self, args):
        cfg = self.get_config()
        user = cfg["user"]
        host = cfg["host"]
        token = getpass(f"Personal Access Token for {user}@{host}: ")
        keyring.set_password(KEYRING_SERVICE, user, token)
        http = HttpClient(base_url=host, token=token, timeout=cfg.get("timeout", 20))
        client = ConfluenceClient(http)
        try:
            me = client.whoami()
            display = me.get("displayName", user)
            print(f"logged in as {display}")
        except HwikiHttpError as e:
            print(f"ERROR: login failed: {e.status_code} {e.body}", file=sys.stderr)
            try:
                keyring.delete_password(KEYRING_SERVICE, user)
            except Exception:
                pass
            sys.exit(3)
