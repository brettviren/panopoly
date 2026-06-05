"""CLI-level tests for all panopoly subcommands."""
import os
import subprocess
import pytest
from pathlib import Path
from click.testing import CliRunner

from panopoly.cli import cli
from panopoly.core import PANOPOLY_MARKER, PanopolyRoot
from panopoly.ops import add_env, add_project, add_source, init_area  # noqa: F401


# ── init ──────────────────────────────────────────────────────────────────────

# ── -h short help ─────────────────────────────────────────────────────────────

def test_top_level_short_help(runner):
    result = runner.invoke(cli, ["-h"])
    assert result.exit_code == 0
    assert "panopoly" in result.output.lower()


def test_init_short_help(runner):
    result = runner.invoke(cli, ["init", "-h"])
    assert result.exit_code == 0


def test_env_enter_short_help(runner):
    result = runner.invoke(cli, ["env", "enter", "-h"])
    assert result.exit_code == 0
    assert "--action" in result.output


# ── init ──────────────────────────────────────────────────────────────────────

def test_init_creates_area(runner, tmp_path):
    result = runner.invoke(cli, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / PANOPOLY_MARKER).is_dir()
    assert (tmp_path / "source").is_dir()
    assert (tmp_path / "project").is_dir()
    assert (tmp_path / "env").is_dir()


def test_init_default_directory(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / PANOPOLY_MARKER).is_dir()


def test_init_idempotent(runner, tmp_path):
    runner.invoke(cli, ["init", str(tmp_path)])
    result = runner.invoke(cli, ["init", str(tmp_path)])
    assert result.exit_code == 0


def test_init_with_layout(runner, tmp_path, git_origin):
    local_config = tmp_path / PANOPOLY_MARKER
    local_config.mkdir(parents=True)
    (local_config / "config.toml").write_text(
        f'[layout.mylay]\nsources = ["{git_origin}"]\nprojects = ["projX"]\n'
    )
    result = runner.invoke(cli, ["init", str(tmp_path), "--layout", "mylay"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "source" / "origin.git").is_dir()
    assert (tmp_path / "project" / "projX").is_dir()


def test_init_layout_missing_errors(runner, tmp_path):
    init_area(tmp_path)
    result = runner.invoke(cli, ["--root", str(tmp_path), "init", str(tmp_path), "--layout", "missing"])
    assert result.exit_code != 0


# ── source add ────────────────────────────────────────────────────────────────

def test_source_add(runner, panopoly_area, git_origin):
    result = runner.invoke(cli, ["--root", str(panopoly_area), "source", "add", str(git_origin)])
    assert result.exit_code == 0, result.output
    assert (panopoly_area / "source" / "origin.git").is_dir()


def test_source_add_output(runner, panopoly_area, git_origin):
    result = runner.invoke(cli, ["--root", str(panopoly_area), "source", "add", str(git_origin)])
    assert "origin.git" in result.output


def test_source_add_help(runner):
    result = runner.invoke(cli, ["source", "add", "--help"])
    assert result.exit_code == 0
    assert "GITURL" in result.output


def test_source_add_short_help(runner):
    result = runner.invoke(cli, ["source", "add", "-h"])
    assert result.exit_code == 0
    assert "GITURL" in result.output


# ── project add ───────────────────────────────────────────────────────────────

def test_project_add(runner, area_with_source):
    root = area_with_source
    result = runner.invoke(
        cli, ["--root", str(root.path), "project", "add", "projX"]
    )
    assert result.exit_code == 0, result.output
    assert root.project_src("projX", "origin").is_dir()


def test_project_add_creates_envrc(runner, area_with_source):
    root = area_with_source
    runner.invoke(cli, ["--root", str(root.path), "project", "add", "projX"])
    assert (root.project_dir("projX") / ".envrc").exists()


def test_project_add_narrow_sources(runner, area_with_source):
    root = area_with_source
    result = runner.invoke(
        cli, ["--root", str(root.path), "project", "add", "projX", "origin"]
    )
    assert result.exit_code == 0, result.output


def test_project_add_with_branch(runner, area_with_source):
    root = area_with_source
    result = runner.invoke(
        cli, ["--root", str(root.path), "project", "add", "projX", "--branch", "main"]
    )
    assert result.exit_code == 0, result.output
    assert root.project_src("projX", "origin").is_dir()


def test_project_add_creates_new_branch(runner, area_with_source):
    root = area_with_source
    result = runner.invoke(
        cli,
        ["--root", str(root.path), "project", "add", "projX", "--branch", "feature/cli"],
    )
    assert result.exit_code == 0, result.output
    wt = root.project_src("projX", "origin")
    branch_result = subprocess.run(
        ["git", "-C", str(wt), "branch", "--show-current"],
        capture_output=True, text=True, check=True,
    )
    assert branch_result.stdout.strip() == "feature/cli"


def test_project_add_help(runner):
    result = runner.invoke(cli, ["project", "add", "--help"])
    assert result.exit_code == 0


# ── env add ───────────────────────────────────────────────────────────────────

def test_env_add(runner, area_with_project):
    root = area_with_project
    result = runner.invoke(cli, ["--root", str(root.path), "env", "add", "host"])
    assert result.exit_code == 0, result.output
    assert root.env_dir("host").is_dir()
    assert (root.env_dir("host") / ".envrc").exists()


def test_env_add_creates_run_envrc(runner, area_with_project):
    root = area_with_project
    runner.invoke(cli, ["--root", str(root.path), "env", "add", "host"])
    run_envrc = root.env_run("host", "projX") / ".envrc"
    assert run_envrc.exists()
    content = run_envrc.read_text()
    assert 'source_env "$_P_ENV/.envrc"' in content
    assert 'source_env "$_P_ROOT/project/$_P_PROJ/.envrc"' in content


def test_env_add_with_spack(runner, area_with_project, tmp_path):
    root = area_with_project
    fake_spack = tmp_path / "spack"
    fake_spack.mkdir()
    result = runner.invoke(
        cli,
        ["--root", str(root.path), "env", "add", "host", f"--spack={fake_spack}"],
    )
    assert result.exit_code == 0, result.output
    assert root.env_spack("host").is_symlink()


def test_env_add_help(runner):
    result = runner.invoke(cli, ["env", "add", "--help"])
    assert result.exit_code == 0


# ── env enter ─────────────────────────────────────────────────────────────────

def test_env_enter_host_execs_shell(runner, area_with_project, monkeypatch):
    root = area_with_project
    add_env(root, "host")

    calls = []
    monkeypatch.setattr("panopoly.commands.env._exec_host", lambda d, s: calls.append((d, s)))
    monkeypatch.setenv("SHELL", "/bin/bash")

    result = runner.invoke(
        cli, ["--root", str(root.path), "env", "enter", "projX"]
    )
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert calls[0][0] == root.env_run("host", "projX")
    assert calls[0][1] == "/bin/bash"


def test_env_enter_default_env_is_host(runner, area_with_project, monkeypatch):
    root = area_with_project
    add_env(root, "host")

    calls = []
    monkeypatch.setattr("panopoly.commands.env._exec_host", lambda d, s: calls.append((d, s)))
    runner.invoke(cli, ["--root", str(root.path), "env", "enter", "projX"])
    assert calls[0][0] == root.env_run("host", "projX")


def test_env_enter_container_run(runner, area_with_project, monkeypatch):
    root = area_with_project
    # Write image config to disk so the CLI re-reads it via load_config
    (root.path / PANOPOLY_MARKER / "config.toml").write_text(
        '[env.el9]\nimage = "el9-img"\n'
    )
    add_env(PanopolyRoot(root.path, {"env": {"el9": {"image": "el9-img"}}}), "el9")

    captured = []
    monkeypatch.setattr("subprocess.run", lambda cmd, **kw: captured.append(cmd))
    monkeypatch.setenv("SHELL", "/bin/bash")

    result = runner.invoke(
        cli, ["--root", str(root.path), "env", "enter", "--env", "el9", "projX"]
    )
    assert result.exit_code == 0, result.output
    assert captured[0][0] == "podman"
    assert "run" in captured[0]
    assert "el9-img" in captured[0]
    assert "/bin/bash" in captured[0]


def test_env_enter_container_exec(runner, area_with_project, monkeypatch):
    root = area_with_project
    (root.path / PANOPOLY_MARKER / "config.toml").write_text(
        '[env.el9]\nimage = "el9-img"\ncontainer = "my-el9"\n'
    )
    add_env(PanopolyRoot(root.path, {"env": {"el9": {"image": "el9-img"}}}), "el9")

    captured = []
    monkeypatch.setattr("subprocess.run", lambda cmd, **kw: captured.append(cmd))
    monkeypatch.setenv("SHELL", "/bin/bash")

    result = runner.invoke(
        cli,
        ["--root", str(root.path), "env", "enter", "--env", "el9", "--action", "exec", "projX"],
    )
    assert result.exit_code == 0, result.output
    assert "exec" in captured[0]
    assert "my-el9" in captured[0]


def test_env_enter_missing_run_dir_errors(runner, panopoly_area):
    result = runner.invoke(
        cli, ["--root", str(panopoly_area), "env", "enter", "projX"]
    )
    assert result.exit_code != 0


def test_env_enter_help(runner):
    result = runner.invoke(cli, ["env", "enter", "--help"])
    assert result.exit_code == 0
    assert "--action" in result.output


# ── config capture ────────────────────────────────────────────────────────────

def test_config_capture_stdout(runner, area_with_project):
    root = area_with_project
    add_env(root, "host")
    result = runner.invoke(cli, ["--root", str(root.path), "config", "capture"])
    assert result.exit_code == 0, result.output
    assert "[source." in result.output
    assert "[project." in result.output
    assert "[env." in result.output


def test_config_capture_to_file(runner, area_with_project, tmp_path):
    root = area_with_project
    outfile = tmp_path / "out.toml"
    result = runner.invoke(
        cli,
        ["--root", str(root.path), "config", "capture", "-o", str(outfile)],
    )
    assert result.exit_code == 0, result.output
    assert outfile.exists()
    assert "[source." in outfile.read_text()


def test_config_capture_narrow(runner, area_with_project):
    root = area_with_project
    result = runner.invoke(
        cli, ["--root", str(root.path), "config", "capture", "source/"]
    )
    assert result.exit_code == 0
    assert "[source." in result.output
    assert "[project." not in result.output


def test_config_capture_help(runner):
    result = runner.invoke(cli, ["config", "capture", "--help"])
    assert result.exit_code == 0
