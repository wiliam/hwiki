from pathlib import Path
from typing import Optional

import sys
import typer

from . import get_client, get_config
from .._http import HwikiHttpError
from .._md_to_storage import md_to_storage

name = "create"
help_text = "Create a new Confluence page"


def run(
    space: str = typer.Option(..., "--space", help="Space key"),
    title: str = typer.Option(..., "--title", help="Page title"),
    file: Optional[Path] = typer.Option(None, "--file", help="Read body from .md file"),
    stdin: bool = typer.Option(False, "--stdin", help="Read body from stdin"),
    parent: Optional[str] = typer.Option(None, "--parent", help="Parent page ID or URL"),
) -> None:
    if file:
        md = file.read_text()
    elif stdin:
        md = sys.stdin.read()
    else:
        md = ""

    storage_xhtml = md_to_storage(md)

    client = get_client()

    parent_id = None
    if parent:
        parent_id = client.resolve_page_id(parent)

    try:
        page = client.create_page(
            space_key=space,
            title=title,
            storage_xhtml=storage_xhtml,
            parent_id=parent_id,
        )
    except HwikiHttpError as e:
        typer.echo(f"ERROR: create: {e.status_code} {e.body}", err=True)
        raise typer.Exit(3)

    host = get_config()["host"].rstrip("/")
    url = f"{host}/pages/{page['id']}"
    typer.echo(f"created page id={page['id']} title={page['title']} url={url}")
