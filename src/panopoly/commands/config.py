"""config command group: configuration utilities."""
from pathlib import Path

import click

from ..cli import cli, pass_pctx, CONTEXT_SETTINGS
from ..ops import capture_config


@cli.group("config", context_settings=CONTEXT_SETTINGS)
def config_group() -> None:
    """Configuration utilities."""


@config_group.command("capture", context_settings=CONTEXT_SETTINGS)
@click.argument("what", nargs=-1)
@click.option(
    "-o", "--output",
    default=None,
    metavar="FILE",
    help="Write TOML to FILE (default: stdout).",
)
@pass_pctx
def config_capture(pctx, what: tuple, output: str) -> None:
    """Inspect the panopoly area and emit TOML configuration.

    Optionally narrow by path: source/, project/projX, env/host
    """
    root = pctx.require_root()
    toml_text = capture_config(root, list(what) if what else None)

    if output:
        Path(output).write_text(toml_text)
        click.echo(f"Wrote config to {output}")
    else:
        click.echo(toml_text, nl=False)
