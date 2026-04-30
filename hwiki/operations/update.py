import sys
from pathlib import Path

from . import HwikiOperation
from .._http import HwikiHttpError
from .._md_to_storage import md_to_storage
from .._text import parse_page_id


class Operation(HwikiOperation):
    def configure_arg_parser(self, subparsers):
        p = subparsers.add_parser("update", help="update an existing Confluence page")
        p.add_argument("page_id", help="page ID or webui URL")
        p.add_argument("--title", help="new page title (optional; defaults to existing title)")
        p.add_argument("--file", help="read body from this .md file")
        p.add_argument("--stdin", action="store_true", help="read body from stdin")
        p.add_argument(
            "--version",
            default="auto",
            metavar="auto|N",
            help="current page version; 'auto' fetches it (default: auto)",
        )
        p.set_defaults(func=self._run, op=self)

    def _run(self, args):
        if not args.file and not args.stdin:
            print("ERROR: update: provide --file or --stdin", file=sys.stderr)
            sys.exit(2)

        pid = parse_page_id(args.page_id)

        if args.version == "auto":
            try:
                page = self.client().get_page(pid)
            except HwikiHttpError as e:
                print(f"ERROR: update {args.page_id}: {e.status_code} {e.body}", file=sys.stderr)
                sys.exit(3)
            current_version = page["version"]
            title = args.title if args.title else page["title"]
        else:
            try:
                current_version = int(args.version)
            except ValueError:
                print(
                    f"ERROR: update: --version must be 'auto' or an integer, got {args.version!r}",
                    file=sys.stderr,
                )
                sys.exit(2)
            if not args.title:
                print(
                    "ERROR: update: --title is required when --version is specified manually",
                    file=sys.stderr,
                )
                sys.exit(2)
            title = args.title

        if args.file:
            md = Path(args.file).read_text()
        else:
            md = sys.stdin.read()

        storage_xhtml = md_to_storage(md)

        try:
            page = self.client().update_page(
                pid,
                title=title,
                storage_xhtml=storage_xhtml,
                current_version=current_version,
            )
        except HwikiHttpError as e:
            print(f"ERROR: update {args.page_id}: {e.status_code} {e.body}", file=sys.stderr)
            sys.exit(3)

        print(f"updated page id={page['id']} version={page['version']} title={page['title']}")
