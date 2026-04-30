from pathlib import Path
from typing import Optional

import sys
import typer

from . import get_client
from .._http import HwikiHttpError
from .._md_to_storage import md_to_storage

name = "update"
help_text = "Update an existing Confluence page"


def run(
    page_id: str = typer.Argument(..., help="Page ID or webui URL"),
    title: Optional[str] = typer.Option(None, "--title", help="New title (keeps existing if omitted)"),
    file: Optional[Path] = typer.Option(None, "--file", help="Read body from .md file"),
    stdin: bool = typer.Option(False, "--stdin", help="Read body from stdin"),
    version: str = typer.Option("auto", "--version", metavar="auto|N",
                                 help="Current version or 'auto' to fetch"),
) -> None:
    if not file and not stdin:
        typer.echo("ERROR: update: provide --file or --stdin", err=True)
        raise typer.Exit(2)

    client = get_client()
    pid = client.resolve_page_id(page_id)

    if version == "auto":
        try:
            page = client.get_page(pid)
        except HwikiHttpError as e:
            typer.echo(f"ERROR: update {page_id}: {e.status_code} {e.body}", err=True)
            raise typer.Exit(3)
        current_version = page["version"]
        title = title if title else page["title"]
    else:
        try:
            current_version = int(version)
        except ValueError:
            typer.echo(
                f"ERROR: update: --version must be 'auto' or an integer, got {version!r}",
                err=True,
            )
            raise typer.Exit(2)
        if not title:
            typer.echo(
                "ERROR: update: --title is required when --version is specified manually",
                err=True,
            )
            raise typer.Exit(2)

    if file:
        md = file.read_text()
    else:
        md = sys.stdin.read()

    storage_xhtml = md_to_storage(md)

    try:
        page = client.update_page(
            pid,
            title=title,
            storage_xhtml=storage_xhtml,
            current_version=current_version,
        )
    except HwikiHttpError as e:
        typer.echo(f"ERROR: update {page_id}: {e.status_code} {e.body}", err=True)
        raise typer.Exit(3)

    typer.echo(f"updated page id={page['id']} version={page['version']} title={page['title']}")
