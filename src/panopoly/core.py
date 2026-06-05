"""Core panopoly utilities: root detection, config loading, path helpers."""
import logging
import os
import tomllib
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

PANOPOLY_MARKER = ".panopoly"


def find_root(start: Optional[Path] = None) -> Path:
    """Walk up from start (default: cwd) looking for a .panopoly/ directory."""
    current = Path(start).resolve() if start else Path.cwd()
    while True:
        if (current / PANOPOLY_MARKER).is_dir():
            return current
        parent = current.parent
        if parent == current:
            raise FileNotFoundError(
                f"No panopoly root found (no {PANOPOLY_MARKER}/ directory) "
                f"starting from {Path(start or Path.cwd()).resolve()}"
            )
        current = parent


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base; override wins on conflicts."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(root: Path) -> dict:
    """Merge ~/.config/panopoly/config.toml with .panopoly/config.toml.

    Local sections override user sections key-by-key at every nesting level.
    """
    xdg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    user_path = xdg / "panopoly" / "config.toml"
    local_path = Path(root) / PANOPOLY_MARKER / "config.toml"

    config: dict = {}

    if user_path.exists():
        with open(user_path, "rb") as fh:
            config = tomllib.load(fh)
        log.debug("loaded user config from %s", user_path)

    if local_path.exists():
        with open(local_path, "rb") as fh:
            local = tomllib.load(fh)
        log.debug("loaded local config from %s", local_path)
        config = _deep_merge(config, local)

    return config


class PanopolyRoot:
    """A resolved panopoly root directory with merged configuration."""

    def __init__(self, path: Path, config: dict) -> None:
        self.path = Path(path).resolve()
        self.config = config

    @classmethod
    def from_path(cls, path: Path) -> "PanopolyRoot":
        path = Path(path).resolve()
        if not (path / PANOPOLY_MARKER).is_dir():
            raise FileNotFoundError(
                f"{path} is not a panopoly root (missing {PANOPOLY_MARKER}/)"
            )
        return cls(path, load_config(path))

    @classmethod
    def find(cls, start: Optional[Path] = None) -> "PanopolyRoot":
        root = find_root(start)
        return cls(root, load_config(root))

    # ── path helpers ─────────────────────────────────────────────────────────

    def source_dir(self) -> Path:
        return self.path / "source"

    def source_repo(self, name: str) -> Path:
        """source/<name>.git bare repo path."""
        bare = name if name.endswith(".git") else f"{name}.git"
        return self.source_dir() / bare

    def source_repos(self) -> list[str]:
        """Names of all bare repos (without .git suffix)."""
        src = self.source_dir()
        if not src.exists():
            return []
        return sorted(
            p.name.removesuffix(".git")
            for p in src.iterdir()
            if p.name.endswith(".git") and p.is_dir()
        )

    def project_dir(self, proj: Optional[str] = None) -> Path:
        base = self.path / "project"
        return base / proj if proj else base

    def project_src(self, proj: str, repo: Optional[str] = None) -> Path:
        base = self.project_dir(proj) / "src"
        return base / repo if repo else base

    def project_repos(self, proj: str) -> list[str]:
        """Names of repos checked out in project/<proj>/src/."""
        src = self.project_src(proj)
        if not src.exists():
            return []
        return sorted(p.name for p in src.iterdir() if p.is_dir())

    def projects(self) -> list[str]:
        """Names of all projects."""
        pd = self.project_dir()
        if not pd.exists():
            return []
        return sorted(p.name for p in pd.iterdir() if p.is_dir())

    def env_dir(self, env: Optional[str] = None) -> Path:
        base = self.path / "env"
        return base / env if env else base

    def env_spack(self, env: str) -> Path:
        return self.env_dir(env) / "spack"

    def env_views(self, env: str, proj: Optional[str] = None) -> Path:
        base = self.env_dir(env) / "views"
        return base / proj if proj else base

    def env_build(
        self,
        env: str,
        proj: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> Path:
        base = self.env_dir(env) / "build"
        if proj:
            base = base / proj
        if repo:
            base = base / repo
        return base

    def env_run(self, env: str, proj: Optional[str] = None) -> Path:
        base = self.env_dir(env) / "run"
        return base / proj if proj else base

    def envs(self) -> list[str]:
        """Names of all environments."""
        ed = self.env_dir()
        if not ed.exists():
            return []
        return sorted(p.name for p in ed.iterdir() if p.is_dir())
