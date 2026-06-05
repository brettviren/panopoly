"""init command: bootstrap a new panopoly area."""
from pathlib import Path

import click

from ..cli import cli
from ..core import PanopolyRoot, load_config
from ..ops import apply_layout, init_area


@cli.command("init")
@click.argument("directory", default=".", required=False)
@click.option(
    "--layout",
    default=None,
    metavar="NAME",
    help="Apply layout from config [layout.<NAME>].",
)
def init_cmd(directory: str, layout: str) -> None:
    """Initialize a panopoly area in DIRECTORY (default: current directory)."""
    root_path = Path(directory).resolve()
    init_area(root_path)

    if layout:
        config = load_config(root_path)
        root = PanopolyRoot(root_path, config)
        apply_layout(root, layout)

    click.echo(f"Initialized panopoly area at {root_path}")
