from pathlib import Path
from typing import Optional

import typer

from . import get_client
from .._http import HwikiHttpError

name = "attach"
help_text = "Upload a file attachment to a Confluence page"


def run(
    page_id: str = typer.Argument(..., help="Page ID or webui URL"),
    file: Path = typer.Argument(..., help="File to attach"),
    message: Optional[str] = typer.Option(None, "-m", "--message", help="Attachment comment"),
) -> None:
    client = get_client()
    pid = client.resolve_page_id(page_id)

    if not file.exists():
        typer.echo(f"ERROR: attach: file not found: {file}", err=True)
        raise typer.Exit(2)

    try:
        attachment = client.upload_attachment(
            pid,
            file,
            comment=message,
        )
    except HwikiHttpError as e:
        typer.echo(f"ERROR: attach {page_id}: {e.status_code} {e.body}", err=True)
        raise typer.Exit(3)

    typer.echo(f"attached {attachment['filename']} id={attachment['id']} to page {pid}")
