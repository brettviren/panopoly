from .cli import cli
from . import commands  # noqa: F401 — registers all subcommands with cli


def main() -> None:
    cli()
