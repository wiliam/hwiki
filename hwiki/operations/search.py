import json
import sys

import typer

from . import get_client
from .._http import HwikiHttpError

name = "search"
help_text = "Search Confluence pages with CQL"


def run(
    cql: str = typer.Argument(..., help="CQL query string"),
    limit: int = typer.Option(25, "-n", "--limit", metavar="N", help="Max results"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    try:
        hits = get_client().search_pages(cql, limit=limit)
    except HwikiHttpError as e:
        typer.echo(f"ERROR: search: {e.status_code} {e.body}", err=True)
        raise typer.Exit(3)

    if as_json:
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
