import sys
from pathlib import Path

from . import HwikiOperation
from .._http import HwikiHttpError
from .._md_to_storage import md_to_storage


class Operation(HwikiOperation):
    def configure_arg_parser(self, subparsers):
        p = subparsers.add_parser("create", help="create a new Confluence page")
        p.add_argument("--space", required=True, help="space key")
        p.add_argument("--title", required=True, help="page title")
        p.add_argument("--file", help="read body from this .md file")
        p.add_argument("--stdin", action="store_true", help="read body from stdin")
        p.add_argument("--parent", help="parent page ID or URL (optional)")
        p.set_defaults(func=self._run, op=self)

    def _run(self, args):
        if args.file:
            md = Path(args.file).read_text()
        elif args.stdin:
            md = sys.stdin.read()
        else:
            md = ""

        storage_xhtml = md_to_storage(md)

        parent_id = None
        if args.parent:
            parent_id = self.client().resolve_page_id(args.parent)

        try:
            page = self.client().create_page(
                space_key=args.space,
                title=args.title,
                storage_xhtml=storage_xhtml,
                parent_id=parent_id,
            )
        except HwikiHttpError as e:
            print(f"ERROR: create: {e.status_code} {e.body}", file=sys.stderr)
            sys.exit(3)

        host = self.get_config()["host"].rstrip("/")
        url = f"{host}/pages/{page['id']}"
        print(f"created page id={page['id']} title={page['title']} url={url}")
