"""Click CLI group and shared context for panopoly."""
import logging
import sys
from pathlib import Path
from typing import Optional

import click

from .core import PanopolyRoot

log = logging.getLogger(__name__)


class PanopolyContext:
    """Carries resolved panopoly state through Click context."""

    def __init__(self, root: Optional[PanopolyRoot] = None) -> None:
        self.root = root

    def require_root(self) -> PanopolyRoot:
        if self.root is None:
            raise click.UsageError(
                "Not inside a panopoly area. Run 'panopoly init' first "
                "or use --root to specify the root directory."
            )
        return self.root


pass_pctx = click.make_pass_decorator(PanopolyContext, ensure=True)


def _setup_logging(level: str, log_file: Optional[str]) -> None:
    numeric = getattr(logging, level.upper(), logging.INFO)
    sink = open(log_file, "a") if log_file else sys.stderr  # noqa: WPS515
    handler = logging.StreamHandler(sink)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=numeric, handlers=[handler], force=True)


@click.group()
@click.option(
    "--root",
    type=click.Path(file_okay=False),
    default=None,
    metavar="DIR",
    help="Panopoly root directory (auto-detected by default).",
)
@click.option(
    "--log-level",
    default="info",
    show_default=True,
    type=click.Choice(["debug", "info", "warning", "error"], case_sensitive=False),
    help="Logging verbosity.",
)
@click.option(
    "--log-file",
    default=None,
    metavar="FILE",
    help="Write log output to FILE instead of stderr.",
)
@click.pass_context
def cli(
    ctx: click.Context,
    root: Optional[str],
    log_level: str,
    log_file: Optional[str],
) -> None:
    """Manage a panopoly development area."""
    _setup_logging(log_level, log_file)
    ctx.ensure_object(PanopolyContext)

    if root:
        try:
            ctx.obj.root = PanopolyRoot.from_path(Path(root))
        except FileNotFoundError as exc:
            raise click.BadParameter(str(exc), param_hint="--root") from exc
    else:
        try:
            ctx.obj.root = PanopolyRoot.find()
        except FileNotFoundError:
            ctx.obj.root = None  # init command creates the root; others will fail explicitly


# Command modules register themselves here when implemented.
# Each commands/<name>.py does: from panopoly.cli import cli; @cli.command() ...
