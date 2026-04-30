import logging
from importlib import import_module
from pkgutil import walk_packages

import typer

import hwiki.operations
from hwiki.operations import set_verbose

app = typer.Typer(no_args_is_help=True, rich_markup_mode="rich", help="Confluence CLI")


@app.callback()
def callback(
    verbose: bool = typer.Option(False, "-v", "--verbose",
                                 help="Print HTTP calls and payloads to stderr"),
):
    if verbose:
        set_verbose(True)
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger("httpx").setLevel(logging.WARNING)


for _mi in walk_packages(hwiki.operations.__path__, hwiki.operations.__name__ + "."):
    _mod = import_module(_mi.name)
    if hasattr(_mod, "run"):
        _name = getattr(_mod, "name", _mi.name.split(".")[-1])
        _help = getattr(_mod, "help_text", None)
        app.command(name=_name, help=_help)(_mod.run)


def main():
    app()


if __name__ == "__main__":
    main()
