import json
import sys
from pathlib import Path

from . import HwikiOperation
from .._http import HwikiHttpError
from .._storage_to_md import storage_to_md
from .._text import parse_page_id


class Operation(HwikiOperation):
    def configure_arg_parser(self, subparsers):
        p = subparsers.add_parser("get", help="fetch a Confluence page")
        p.add_argument("page_id", help="page ID or webui URL")
        p.add_argument("--raw", action="store_true", help="output raw storage XHTML")
        p.add_argument("--json", dest="as_json", action="store_true")
        p.add_argument("-o", "--out", help="write to file instead of stdout")
        p.set_defaults(func=self._run, op=self)

    def _run(self, args):
        pid = parse_page_id(args.page_id)
        try:
            page = self.client().get_page(pid)
        except HwikiHttpError as e:
            print(f"ERROR: get {args.page_id}: {e.status_code} {e.body}", file=sys.stderr)
            sys.exit(3)

        if args.as_json:
            json.dump(page, sys.stdout, ensure_ascii=False, indent=2)
            print()
            return

        body = page["body_storage"] if args.raw else storage_to_md(page["body_storage"])
        if args.out:
            Path(args.out).write_text(body)
        else:
            print(body)
