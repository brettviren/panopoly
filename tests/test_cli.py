"""Tests for the top-level CLI group (options, context, root resolution)."""
from pathlib import Path

import pytest
from click.testing import CliRunner

from panopoly.cli import cli
from panopoly.core import PANOPOLY_MARKER


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def panopoly_area(tmp_path):
    (tmp_path / PANOPOLY_MARKER).mkdir()
    (tmp_path / "source").mkdir()
    (tmp_path / "project").mkdir()
    (tmp_path / "env").mkdir()
    return tmp_path


def test_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "panopoly" in result.output.lower()


def test_log_level_option_accepted(runner, panopoly_area):
    result = runner.invoke(cli, ["--root", str(panopoly_area), "--log-level", "debug", "--help"])
    assert result.exit_code == 0


def test_explicit_root_resolved(runner, panopoly_area):
    result = runner.invoke(cli, ["--root", str(panopoly_area), "--help"])
    assert result.exit_code == 0


def test_invalid_root_gives_error(runner, tmp_path):
    no_marker = tmp_path / "notaroot"
    no_marker.mkdir()
    # --help short-circuits before the callback; invoke without it so validation runs
    result = runner.invoke(cli, ["--root", str(no_marker)])
    assert result.exit_code != 0
    assert "error" in result.output.lower()
