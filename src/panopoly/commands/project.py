"""project command group: manage project worktree areas."""
import click

from ..cli import cli, pass_pctx
from ..ops import add_project


@cli.group("project")
def project_group() -> None:
    """Manage projects."""


@project_group.command("add")
@click.argument("name")
@click.argument("sources", nargs=-1)
@pass_pctx
def project_add(pctx, name: str, sources: tuple) -> None:
    """Add project NAME with worktrees for SOURCES (default: all source repos)."""
    root = pctx.require_root()
    src_list = list(sources) if sources else None
    dest = add_project(root, name, src_list)
    click.echo(f"Added project at {dest}")
