"""source command group: manage bare git repos in source/."""
import click

from ..cli import cli, pass_pctx
from ..ops import add_source


@cli.group("source")
def source_group() -> None:
    """Manage source repositories."""


@source_group.command("add")
@click.argument("giturl")
@pass_pctx
def source_add(pctx, giturl: str) -> None:
    """Add a bare git clone of GITURL to source/."""
    root = pctx.require_root()
    dest = add_source(root, giturl)
    click.echo(f"Added source repo at {dest}")
