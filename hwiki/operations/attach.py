import sys
from pathlib import Path

from . import HwikiOperation
from .._http import HwikiHttpError


class Operation(HwikiOperation):
    def configure_arg_parser(self, subparsers):
        p = subparsers.add_parser("attach", help="upload a file attachment to a Confluence page")
        p.add_argument("page_id", help="page ID or webui URL")
        p.add_argument("file", help="path to the file to attach")
        p.add_argument("-m", "--message", dest="comment", help="attachment comment")
        p.set_defaults(func=self._run, op=self)

    def _run(self, args):
        pid = self.client().resolve_page_id(args.page_id)
        file_path = Path(args.file)

        if not file_path.exists():
            print(f"ERROR: attach: file not found: {args.file}", file=sys.stderr)
            sys.exit(2)

        try:
            attachment = self.client().upload_attachment(
                pid,
                file_path,
                comment=args.comment,
            )
        except HwikiHttpError as e:
            print(f"ERROR: attach {args.page_id}: {e.status_code} {e.body}", file=sys.stderr)
            sys.exit(3)

        print(f"attached {attachment['filename']} id={attachment['id']} to page {pid}")
