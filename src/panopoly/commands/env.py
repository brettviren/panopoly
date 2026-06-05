"""env command group: manage named runtime environments."""
import os
import subprocess
from pathlib import Path

import click

from ..cli import cli, pass_pctx
from ..ops import add_env


@cli.group("env")
def env_group() -> None:
    """Manage environments."""


@env_group.command("add")
@click.argument("name")
@click.argument("projects", nargs=-1)
@click.option(
    "--spack",
    default=None,
    metavar="PATH",
    help="Path to an existing Spack installation to symlink as spack/.",
)
@pass_pctx
def env_add(pctx, name: str, projects: tuple, spack: str) -> None:
    """Add environment NAME with structure for PROJECTS (default: all projects)."""
    root = pctx.require_root()
    proj_list = list(projects) if projects else None
    dest = add_env(root, name, proj_list, spack)
    click.echo(f"Added environment at {dest}")


@env_group.command("enter")
@click.argument("projname")
@click.option(
    "-e", "--env", "env_name",
    default="host",
    show_default=True,
    help="Environment name.",
)
@click.option(
    "--action",
    default="run",
    show_default=True,
    type=click.Choice(["run", "exec"], case_sensitive=False),
    help="Container action: 'run' starts a new container, 'exec' attaches to running.",
)
@pass_pctx
def env_enter(pctx, projname: str, env_name: str, action: str) -> None:
    """Enter the run environment for PROJNAME in environment ENV_NAME."""
    root = pctx.require_root()
    run_dir = root.env_run(env_name, projname)

    if not run_dir.exists():
        raise click.UsageError(
            f"Run directory does not exist: {run_dir}\n"
            f"Run 'panopoly env add {env_name} {projname}' first."
        )

    image = root.config.get("env", {}).get(env_name, {}).get("image")

    if image is None:
        shell = os.environ.get("SHELL", "/bin/bash")
        _exec_host(run_dir, shell)
    else:
        _run_container(root, env_name, projname, image, action)


def _exec_host(run_dir: Path, shell: str) -> None:
    """Replace the current process with shell running in run_dir."""
    os.chdir(run_dir)
    os.execvp(shell, [shell])


def _run_container(root, env_name: str, projname: str, image: str, action: str) -> None:
    shell = os.environ.get("SHELL", "/bin/bash")
    if action == "run":
        cmd = [
            "podman", "run", "-it",
            "-v", f"{root.project_dir()}:/project:ro",
            "-v", f"{root.source_dir()}:/source:ro",
            "-v", f"{root.env_dir(env_name)}:/env:rw",
            image,
            shell,
        ]
    else:
        container = root.config.get("env", {}).get(env_name, {}).get("container", env_name)
        cmd = ["podman", "exec", "-it", container, shell]

    subprocess.run(cmd, check=True)
