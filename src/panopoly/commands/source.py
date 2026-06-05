"""source command group: manage bare git repos in source/."""
import click

from ..cli import cli, pass_pctx, CONTEXT_SETTINGS
from ..ops import add_source, _get_remote_url


@cli.group("source", context_settings=CONTEXT_SETTINGS)
def source_group() -> None:
    """Manage source repositories."""


@source_group.command("add", context_settings=CONTEXT_SETTINGS)
@click.argument("giturl")
@pass_pctx
def source_add(pctx, giturl: str) -> None:
    """Add a bare git clone of GITURL to source/."""
    root = pctx.require_root()
    dest = add_source(root, giturl)
    click.echo(f"Added source repo at {dest}")


@source_group.command("list", context_settings=CONTEXT_SETTINGS)
@pass_pctx
def source_list(pctx) -> None:
    """List source repositories with their remote origin URL."""
    root = pctx.require_root()
    repos = root.source_repos()
    if not repos:
        return
    width = max(len(r) for r in repos)
    for name in repos:
        url = _get_remote_url(root.source_repo(name)) or "(no remote)"
        click.echo(f"{name:<{width}}  {url}")
