import json
import sys
from typing import Optional
from pathlib import Path

import typer

from . import get_client, get_config
from .._http import HwikiHttpError
from .._storage_to_md import storage_to_md

name = "get"
help_text = "Fetch a Confluence page as Markdown"


def run(
    page_id: str = typer.Argument(..., help="Page ID or webui URL"),
    raw: bool = typer.Option(False, "--raw", help="Output raw storage XHTML"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    out: Optional[Path] = typer.Option(None, "-o", "--out", help="Write to file"),
) -> None:
    client = get_client()
    pid = client.resolve_page_id(page_id)
    try:
        page = client.get_page(pid)
    except HwikiHttpError as e:
        typer.echo(f"ERROR: get {page_id}: {e.status_code} {e.body}", err=True)
        raise typer.Exit(3)

    if as_json:
        json.dump(page, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return

    if raw:
        body = page["body_storage"]
    else:
        cfg = get_config()
        body = storage_to_md(
            page["body_storage"],
            host=cfg["host"],
            space_key=page["space_key"],
            page_id=page["id"],
        )

    if out:
        out.write_text(body)
    else:
        print(body)
