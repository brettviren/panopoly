"""project command group: manage project worktree areas."""
import click

from ..cli import cli, pass_pctx, CONTEXT_SETTINGS
from ..ops import add_project


@cli.group("project", context_settings=CONTEXT_SETTINGS)
def project_group() -> None:
    """Manage projects."""


@project_group.command("add", context_settings=CONTEXT_SETTINGS)
@click.argument("name")
@click.argument("sources", nargs=-1)
@click.option(
    "--branch",
    default=None,
    metavar="BRANCH",
    help="Branch name for worktrees. Checked out if it exists; created if it does not.",
)
@click.option(
    "--ref",
    default=None,
    metavar="REF",
    help="Starting commit/branch/tag for creating BRANCH when it does not yet exist.",
)
@pass_pctx
def project_add(pctx, name: str, sources: tuple, branch: str, ref: str) -> None:
    """Add project NAME with worktrees for SOURCES (default: all source repos).

    If --branch is given, each worktree uses that branch (creating it from --ref
    or HEAD if the branch does not already exist in the bare repo).
    """
    root = pctx.require_root()
    src_list = list(sources) if sources else None
    dest = add_project(root, name, src_list, branch=branch, ref=ref)
    click.echo(f"Added project at {dest}")
