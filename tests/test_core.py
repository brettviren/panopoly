"""Tests for root detection and config loading in panopoly.core."""
import pytest
from pathlib import Path

from panopoly.core import (
    PANOPOLY_MARKER,
    PanopolyRoot,
    _deep_merge,
    find_root,
    load_config,
)


# ── find_root ─────────────────────────────────────────────────────────────────

def test_find_root_at_start(tmp_path):
    (tmp_path / PANOPOLY_MARKER).mkdir()
    assert find_root(tmp_path) == tmp_path


def test_find_root_walks_up(tmp_path):
    (tmp_path / PANOPOLY_MARKER).mkdir()
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    assert find_root(deep) == tmp_path


def test_find_root_not_found(tmp_path):
    with pytest.raises(FileNotFoundError, match=PANOPOLY_MARKER):
        find_root(tmp_path)


def test_find_root_stops_at_nearest(tmp_path):
    """When nested .panopoly/ dirs exist, the nearest one wins."""
    (tmp_path / PANOPOLY_MARKER).mkdir()
    inner = tmp_path / "sub"
    inner.mkdir()
    (inner / PANOPOLY_MARKER).mkdir()
    assert find_root(inner) == inner


# ── _deep_merge ───────────────────────────────────────────────────────────────

def test_deep_merge_flat_override():
    result = _deep_merge({"a": 1, "b": 2}, {"b": 99})
    assert result == {"a": 1, "b": 99}


def test_deep_merge_nested_override():
    base = {"env": {"host": {"image": "old"}, "el9": {"image": "el9-img"}}}
    override = {"env": {"host": {"image": "new"}}}
    result = _deep_merge(base, override)
    assert result["env"]["host"]["image"] == "new"
    assert result["env"]["el9"]["image"] == "el9-img"  # untouched


def test_deep_merge_adds_keys():
    result = _deep_merge({"a": 1}, {"b": 2})
    assert result == {"a": 1, "b": 2}


def test_deep_merge_does_not_mutate_base():
    base = {"x": {"y": 1}}
    _deep_merge(base, {"x": {"y": 2}})
    assert base["x"]["y"] == 1


# ── load_config ───────────────────────────────────────────────────────────────

def test_load_config_empty(tmp_path, monkeypatch):
    (tmp_path / PANOPOLY_MARKER).mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "noconfig"))
    assert load_config(tmp_path) == {}


def test_load_config_user_only(tmp_path, monkeypatch):
    (tmp_path / PANOPOLY_MARKER).mkdir()
    cfg_dir = tmp_path / "cfg" / "panopoly"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config.toml").write_text('[foo]\nbar = 1\n')
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    config = load_config(tmp_path)
    assert config["foo"]["bar"] == 1


def test_load_config_local_overrides_user(tmp_path, monkeypatch):
    (tmp_path / PANOPOLY_MARKER).mkdir()
    cfg_dir = tmp_path / "cfg" / "panopoly"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config.toml").write_text(
        '[env.host]\nimage = "old"\n[env.el9]\nimage = "el9"\n'
    )
    (tmp_path / PANOPOLY_MARKER / "config.toml").write_text(
        '[env.host]\nimage = "new"\n'
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    config = load_config(tmp_path)
    assert config["env"]["host"]["image"] == "new"
    assert config["env"]["el9"]["image"] == "el9"  # not affected by local override


def test_load_config_local_only(tmp_path, monkeypatch):
    (tmp_path / PANOPOLY_MARKER).mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "noconfig"))
    (tmp_path / PANOPOLY_MARKER / "config.toml").write_text('[foo]\nbar = 42\n')
    config = load_config(tmp_path)
    assert config["foo"]["bar"] == 42


# ── PanopolyRoot ──────────────────────────────────────────────────────────────

def test_panopoly_root_from_path(tmp_path):
    (tmp_path / PANOPOLY_MARKER).mkdir()
    root = PanopolyRoot.from_path(tmp_path)
    assert root.path == tmp_path.resolve()


def test_panopoly_root_from_path_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        PanopolyRoot.from_path(tmp_path)


def test_panopoly_root_find(tmp_path):
    (tmp_path / PANOPOLY_MARKER).mkdir()
    deep = tmp_path / "x" / "y"
    deep.mkdir(parents=True)
    root = PanopolyRoot.find(deep)
    assert root.path == tmp_path.resolve()


def _make_root(tmp_path) -> PanopolyRoot:
    (tmp_path / PANOPOLY_MARKER).mkdir()
    return PanopolyRoot(tmp_path, {})


def test_path_helpers_source(tmp_path):
    r = _make_root(tmp_path)
    assert r.source_dir() == tmp_path / "source"
    assert r.source_repo("repoA") == tmp_path / "source" / "repoA.git"
    assert r.source_repo("repoA.git") == tmp_path / "source" / "repoA.git"


def test_path_helpers_project(tmp_path):
    r = _make_root(tmp_path)
    assert r.project_dir() == tmp_path / "project"
    assert r.project_dir("projX") == tmp_path / "project" / "projX"
    assert r.project_src("projX") == tmp_path / "project" / "projX" / "src"
    assert r.project_src("projX", "repoA") == tmp_path / "project" / "projX" / "src" / "repoA"


def test_path_helpers_env(tmp_path):
    r = _make_root(tmp_path)
    assert r.env_dir() == tmp_path / "env"
    assert r.env_dir("host") == tmp_path / "env" / "host"
    assert r.env_spack("host") == tmp_path / "env" / "host" / "spack"
    assert r.env_views("host", "projX") == tmp_path / "env" / "host" / "views" / "projX"
    assert r.env_build("host", "projX", "repoA") == tmp_path / "env" / "host" / "build" / "projX" / "repoA"
    assert r.env_run("host", "projX") == tmp_path / "env" / "host" / "run" / "projX"


def test_source_repos_enumeration(tmp_path):
    r = _make_root(tmp_path)
    src = tmp_path / "source"
    src.mkdir()
    (src / "repoA.git").mkdir()
    (src / "repoB.git").mkdir()
    (src / "not-a-repo").mkdir()  # no .git suffix — excluded
    assert r.source_repos() == ["repoA", "repoB"]


def test_projects_enumeration(tmp_path):
    r = _make_root(tmp_path)
    pd = tmp_path / "project"
    pd.mkdir()
    (pd / "projX").mkdir()
    (pd / "projY").mkdir()
    assert r.projects() == ["projX", "projY"]


def test_envs_enumeration(tmp_path):
    r = _make_root(tmp_path)
    ed = tmp_path / "env"
    ed.mkdir()
    (ed / "host").mkdir()
    (ed / "el9").mkdir()
    assert r.envs() == ["el9", "host"]
