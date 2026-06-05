"""Tests for panopoly.ops high-level operations."""
import subprocess
import pytest
from pathlib import Path

from panopoly.core import PANOPOLY_MARKER, PanopolyRoot
from panopoly.ops import (
    _add_worktree,
    _branch_exists,
    _project_envrc,
    _env_envrc,
    _run_envrc,
    _repo_name_from_url,
    add_env,
    add_project,
    add_source,
    capture_config,
    init_area,
)


# ── init_area ─────────────────────────────────────────────────────────────────

def test_init_area_creates_skeleton(tmp_path):
    init_area(tmp_path)
    assert (tmp_path / PANOPOLY_MARKER).is_dir()
    assert (tmp_path / "source").is_dir()
    assert (tmp_path / "project").is_dir()
    assert (tmp_path / "env").is_dir()


def test_init_area_idempotent(tmp_path):
    init_area(tmp_path)
    init_area(tmp_path)  # should not raise


# ── _repo_name_from_url ───────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("https://github.com/org/repo.git", "repo"),
    ("https://github.com/org/repo", "repo"),
    ("git@github.com:org/repo.git", "repo"),
    ("/local/path/to/origin", "origin"),
    ("/local/path/to/myrepo.git/", "myrepo"),
])
def test_repo_name_from_url(url, expected):
    assert _repo_name_from_url(url) == expected


# ── add_source ────────────────────────────────────────────────────────────────

def test_add_source_clones_bare(proot, git_origin):
    dest = add_source(proot, str(git_origin))
    assert dest.exists()
    assert (dest / "HEAD").exists()  # bare repo marker


def test_add_source_idempotent(proot, git_origin):
    add_source(proot, str(git_origin))
    add_source(proot, str(git_origin))  # should not raise or re-clone


def test_add_source_name_from_url(proot, git_origin):
    dest = add_source(proot, str(git_origin))
    assert dest == proot.source_repo("origin")


# ── add_project ───────────────────────────────────────────────────────────────

def test_add_project_creates_worktree(area_with_source):
    add_project(area_with_source, "projX")
    wt = area_with_source.project_src("projX", "origin")
    assert wt.is_dir()
    assert (wt / "README.md").exists()


def test_add_project_creates_envrc(area_with_source):
    add_project(area_with_source, "projX")
    envrc = area_with_source.project_dir("projX") / ".envrc"
    assert envrc.exists()
    content = envrc.read_text()
    assert "PANOPOLY_PROJECT" in content
    assert "PANOPOLY_WORKTREES" in content
    assert "PANOPOLY_WORKTREE_" in content


def test_add_project_idempotent(area_with_source):
    add_project(area_with_source, "projX")
    add_project(area_with_source, "projX")  # should not raise


def test_add_project_narrow_sources(area_with_source, git_origin, tmp_path):
    """Specifying sources=[] skips all repos without error."""
    add_project(area_with_source, "empty_proj", sources=[])
    assert area_with_source.project_src("empty_proj").is_dir()


def test_add_project_explicit_existing_branch(area_with_source):
    """--branch targeting an existing branch checks it out without creating."""
    add_project(area_with_source, "projX", branch="main")
    wt = area_with_source.project_src("projX", "origin")
    assert (wt / "README.md").exists()
    result = subprocess.run(
        ["git", "-C", str(wt), "branch", "--show-current"],
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip() == "main"


def test_add_project_new_branch_created(area_with_source):
    """--branch with a non-existent name creates the branch from HEAD."""
    add_project(area_with_source, "projX", branch="feature/x")
    wt = area_with_source.project_src("projX", "origin")
    assert (wt / "README.md").exists()
    result = subprocess.run(
        ["git", "-C", str(wt), "branch", "--show-current"],
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip() == "feature/x"


def test_add_project_new_branch_from_ref(area_with_source):
    """--branch with --ref creates the branch from the given ref."""
    add_project(area_with_source, "projX", branch="feature/y", ref="main")
    wt = area_with_source.project_src("projX", "origin")
    result = subprocess.run(
        ["git", "-C", str(wt), "branch", "--show-current"],
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip() == "feature/y"


def test_branch_exists_true(area_with_source):
    bare = area_with_source.source_repo("origin")
    assert _branch_exists(bare, "main") is True


def test_branch_exists_false(area_with_source):
    bare = area_with_source.source_repo("origin")
    assert _branch_exists(bare, "no-such-branch") is False


def test_add_project_missing_source_logged(area_with_source, caplog):
    import logging
    with caplog.at_level(logging.WARNING, logger="panopoly.ops"):
        add_project(area_with_source, "projX", sources=["nonexistent"])
    assert "nonexistent" in caplog.text


# ── project .envrc content ────────────────────────────────────────────────────

def test_project_envrc_sets_project_var():
    content = _project_envrc()
    assert "PANOPOLY_PROJECT" in content


def test_project_envrc_sets_worktrees():
    content = _project_envrc()
    assert "PANOPOLY_WORKTREES" in content


def test_project_envrc_sets_worktree_per_repo():
    content = _project_envrc()
    assert "PANOPOLY_WORKTREE_" in content


# ── add_env ───────────────────────────────────────────────────────────────────

def test_add_env_creates_skeleton(area_with_project):
    root = area_with_project
    add_env(root, "host")
    assert root.env_dir("host").is_dir()
    assert (root.env_dir("host") / "views").is_dir()
    assert (root.env_dir("host") / "build").is_dir()
    assert (root.env_dir("host") / "run").is_dir()


def test_add_env_creates_env_envrc(area_with_project):
    root = area_with_project
    add_env(root, "host")
    envrc = root.env_dir("host") / ".envrc"
    assert envrc.exists()
    assert "PANOPOLY_SPACK" in envrc.read_text()


def test_add_env_creates_project_structure(area_with_project):
    root = area_with_project
    add_env(root, "host")
    assert root.env_views("host", "projX").is_dir()
    assert root.env_build("host", "projX", "origin").is_dir()
    assert root.env_run("host", "projX").is_dir()


def test_add_env_creates_run_envrc(area_with_project):
    root = area_with_project
    add_env(root, "host")
    run_envrc = root.env_run("host", "projX") / ".envrc"
    assert run_envrc.exists()
    content = run_envrc.read_text()
    assert "PANOPOLY_PREFIX" in content
    assert "load_prefix" in content
    assert "source_env" in content


def test_add_env_spack_symlink(area_with_project, tmp_path):
    root = area_with_project
    fake_spack = tmp_path / "spack_install"
    fake_spack.mkdir()
    add_env(root, "host", spack=str(fake_spack))
    spack_link = root.env_spack("host")
    assert spack_link.is_symlink()
    assert spack_link.resolve() == fake_spack


def test_add_env_spack_missing_raises(area_with_project, tmp_path):
    import click
    root = area_with_project
    with pytest.raises(click.UsageError, match="does not exist"):
        add_env(root, "host", spack=str(tmp_path / "no_such_spack"))


def test_add_env_idempotent(area_with_project):
    root = area_with_project
    add_env(root, "host")
    add_env(root, "host")  # should not raise


def test_add_env_narrow_projects(area_with_project, tmp_path):
    root = area_with_project
    add_env(root, "host", projects=[])
    assert not root.env_run("host", "projX").exists()


# ── .envrc template content ───────────────────────────────────────────────────

def test_env_envrc_spack_conditional():
    content = _env_envrc()
    assert "PANOPOLY_SPACK" in content
    assert "PATH_add" in content


def test_run_envrc_sources_env_level():
    content = _run_envrc()
    # env-level .envrc must be sourced (provides PANOPOLY_SPACK / PATH)
    assert 'source_env "$_P_ENV/.envrc"' in content


def test_run_envrc_sources_project_level():
    content = _run_envrc()
    assert 'source_env "$_P_ROOT/project/$_P_PROJ/.envrc"' in content


def test_run_envrc_relative_paths():
    content = _run_envrc()
    assert "../.." in content
    assert "PANOPOLY_PREFIX" in content
    assert "load_prefix" in content


# ── capture_config ────────────────────────────────────────────────────────────

def test_capture_config_sources(area_with_source):
    root = area_with_source
    toml = capture_config(root)
    assert "[source.origin]" in toml
    assert "url = " in toml


def test_capture_config_projects(area_with_project):
    root = area_with_project
    toml = capture_config(root)
    assert "[project.projX]" in toml
    assert '"origin"' in toml


def test_capture_config_envs(area_with_project):
    root = area_with_project
    add_env(root, "host")
    toml = capture_config(root)
    assert "[env.host]" in toml


def test_capture_config_narrow_source(area_with_project):
    root = area_with_project
    add_env(root, "host")
    toml = capture_config(root, ["source/"])
    assert "[source." in toml
    assert "[project." not in toml
    assert "[env." not in toml


def test_capture_config_narrow_project(area_with_project):
    root = area_with_project
    toml = capture_config(root, ["project/projX"])
    assert "[project.projX]" in toml
    assert "[source." not in toml


def test_capture_config_narrow_env(area_with_project):
    root = area_with_project
    add_env(root, "host")
    toml = capture_config(root, ["env/host"])
    assert "[env.host]" in toml
    assert "[source." not in toml
    assert "[project." not in toml


def test_capture_config_env_image(area_with_project):
    root = area_with_project
    root.config.setdefault("env", {})["el9"] = {"image": "el9-img"}
    add_env(root, "el9")
    toml = capture_config(root, ["env/el9"])
    assert 'image = "el9-img"' in toml
