import json
import sys

from . import HwikiOperation
from .._http import HwikiHttpError


class Operation(HwikiOperation):
    def configure_arg_parser(self, subparsers):
        p = subparsers.add_parser("search", help="search Confluence pages with CQL")
        p.add_argument("cql", help="CQL query string")
        p.add_argument("-n", "--limit", type=int, default=25, metavar="N")
        p.add_argument("--json", dest="as_json", action="store_true")
        p.set_defaults(func=self._run, op=self)

    def _run(self, args):
        try:
            hits = self.client().search_pages(args.cql, limit=args.limit)
        except HwikiHttpError as e:
            print(f"ERROR: search: {e.status_code} {e.body}", file=sys.stderr)
            sys.exit(3)

        if args.as_json:
            json.dump(hits, sys.stdout, ensure_ascii=False, indent=2)
            print()
            return

        if not hits:
            return

        id_w = max(len(h["id"]) for h in hits)
        space_w = max(len(h["space_key"]) for h in hits)

        for h in hits:
            print(
                h["id"].ljust(id_w) + "   " +
                h["space_key"].ljust(space_w) + "   " +
                h["title"].ljust(40) + "   " +
                h["url"]
            )
