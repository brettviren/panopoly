"""Shared pytest fixtures."""
import subprocess
import pytest
from pathlib import Path
from click.testing import CliRunner

from panopoly.cli import cli
from panopoly.core import PanopolyRoot, PANOPOLY_MARKER
from panopoly.ops import init_area


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def panopoly_area(tmp_path):
    """An initialized (empty) panopoly area."""
    init_area(tmp_path)
    return tmp_path


@pytest.fixture
def proot(panopoly_area):
    """PanopolyRoot for panopoly_area with empty config."""
    return PanopolyRoot(panopoly_area, {})


@pytest.fixture
def git_origin(tmp_path):
    """A local non-bare git repo with one commit on branch 'main'."""
    repo = tmp_path / "origin"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "T"], check=True)
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True)
    return repo


@pytest.fixture
def area_with_source(panopoly_area, git_origin):
    """Panopoly area that already has one source repo cloned (named 'origin')."""
    from panopoly.ops import add_source
    root = PanopolyRoot(panopoly_area, {})
    add_source(root, str(git_origin))
    return root


@pytest.fixture
def area_with_project(area_with_source):
    """Panopoly area with source + project 'projX' checked out."""
    from panopoly.ops import add_project
    add_project(area_with_source, "projX")
    return area_with_source
