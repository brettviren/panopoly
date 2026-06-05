"""High-level panopoly operations shared by CLI commands."""
import logging
import subprocess
from pathlib import Path
from typing import Optional

import click

from .core import PANOPOLY_MARKER, PanopolyRoot, load_config

log = logging.getLogger(__name__)


# ── area initialization ───────────────────────────────────────────────────────


def init_area(path: Path) -> None:
    """Create the panopoly skeleton at path (idempotent)."""
    path = Path(path)
    (path / PANOPOLY_MARKER).mkdir(parents=True, exist_ok=True)
    for name in ("source", "project", "env"):
        (path / name).mkdir(exist_ok=True)
    log.info("initialized panopoly area at %s", path)


def apply_layout(root: PanopolyRoot, layout_name: str) -> None:
    """Apply a named [layout.<name>] section from config to an initialized area."""
    layout = root.config.get("layout", {}).get(layout_name)
    if layout is None:
        raise click.UsageError(
            f"Layout '{layout_name}' not found in config "
            f"(expected [layout.{layout_name}] section)."
        )
    for url in layout.get("sources", []):
        add_source(root, url)
    for proj in layout.get("projects", []):
        add_project(root, proj)
    for env_name in layout.get("envs", []):
        add_env(root, env_name)


# ── source ────────────────────────────────────────────────────────────────────


def add_source(root: PanopolyRoot, giturl: str) -> Path:
    """Bare-clone giturl into source/<name>.git (idempotent)."""
    name = _repo_name_from_url(giturl)
    dest = root.source_repo(name)
    if dest.exists():
        log.info("source repo %s already exists, skipping", name)
        return dest
    root.source_dir().mkdir(exist_ok=True)
    log.info("cloning %s -> %s", giturl, dest)
    subprocess.run(["git", "clone", "--bare", giturl, str(dest)], check=True)
    return dest


# ── project ───────────────────────────────────────────────────────────────────


def add_project(
    root: PanopolyRoot,
    name: str,
    sources: Optional[list[str]] = None,
    branch: Optional[str] = None,
    ref: Optional[str] = None,
) -> Path:
    """Create project/<name> with git worktrees and a project .envrc (idempotent).

    branch: if given, use this branch for every worktree (creating it when absent).
    ref: starting point when creating a new branch; defaults to the bare repo HEAD.
    """
    proj_dir = root.project_dir(name)
    root.project_src(name).mkdir(parents=True, exist_ok=True)

    repo_names = sources if sources is not None else root.source_repos()
    for repo_name in repo_names:
        bare = root.source_repo(repo_name)
        if not bare.exists():
            log.warning("source repo %s not found, skipping", repo_name)
            continue
        dest = root.project_src(name, repo_name)
        if dest.exists():
            log.info("worktree %s already exists, skipping", dest)
            continue
        _add_worktree(bare, dest, branch, ref)

    envrc = proj_dir / ".envrc"
    if not envrc.exists():
        envrc.write_text(_project_envrc())
        log.info("wrote %s", envrc)

    return proj_dir


# ── env ───────────────────────────────────────────────────────────────────────


def add_env(
    root: PanopolyRoot,
    name: str,
    projects: Optional[list[str]] = None,
    spack: Optional[str] = None,
) -> Path:
    """Create env/<name> skeleton with .envrc files and optional spack symlink (idempotent)."""
    env_dir = root.env_dir(name)
    for subdir in ("views", "build", "run"):
        (env_dir / subdir).mkdir(parents=True, exist_ok=True)

    spack_link = root.env_spack(name)
    if spack and not spack_link.exists():
        spack_path = Path(spack).resolve()
        if not spack_path.exists():
            raise click.UsageError(f"Spack path does not exist: {spack_path}")
        spack_link.symlink_to(spack_path)
        log.info("linked spack: %s -> %s", spack_link, spack_path)

    envrc = env_dir / ".envrc"
    if not envrc.exists():
        envrc.write_text(_env_envrc())
        log.info("wrote %s", envrc)

    proj_names = projects if projects is not None else root.projects()
    for proj in proj_names:
        root.env_views(name, proj).mkdir(exist_ok=True)
        for repo in root.project_repos(proj):
            root.env_build(name, proj, repo).mkdir(parents=True, exist_ok=True)
        run_proj = root.env_run(name, proj)
        run_proj.mkdir(exist_ok=True)
        run_envrc = run_proj / ".envrc"
        if not run_envrc.exists():
            run_envrc.write_text(_run_envrc())
            log.info("wrote %s", run_envrc)

    return env_dir


# ── config capture ────────────────────────────────────────────────────────────


def capture_config(
    root: PanopolyRoot,
    paths: Optional[list[str]] = None,
) -> str:
    """Inspect the area and return a TOML string.

    paths narrows output: e.g. ['source/', 'project/projX', 'env/host'].
    """
    source_names = root.source_repos()
    project_names = root.projects()
    env_names = root.envs()

    emit_sources = True
    emit_projects = True
    emit_envs = True

    if paths:
        emit_sources = emit_projects = emit_envs = False
        for p in paths:
            p = p.strip("/")
            parts = p.split("/", 1)
            head = parts[0]
            tail = parts[1].strip("/") if len(parts) > 1 else ""
            if head == "source":
                emit_sources = True
                if tail:
                    source_names = [tail.removesuffix(".git")]
            elif head == "project":
                emit_projects = True
                if tail:
                    project_names = [tail]
            elif head == "env":
                emit_envs = True
                if tail:
                    env_names = [tail]

    lines: list[str] = []

    if emit_sources:
        for name in source_names:
            bare = root.source_repo(name)
            url = _get_remote_url(bare)
            lines.append(f"[source.{name}]")
            if url:
                lines.append(f'url = "{url}"')
            lines.append("")

    if emit_projects:
        for proj in project_names:
            repos = root.project_repos(proj)
            lines.append(f"[project.{proj}]")
            if repos:
                src_str = ", ".join(f'"{r}"' for r in repos)
                lines.append(f"sources = [{src_str}]")
            lines.append("")

    if emit_envs:
        for env_name in env_names:
            env_cfg = root.config.get("env", {}).get(env_name, {})
            lines.append(f"[env.{env_name}]")
            if "image" in env_cfg:
                lines.append(f'image = "{env_cfg["image"]}"')
            spack_link = root.env_spack(env_name)
            if spack_link.is_symlink():
                lines.append(f'spack = "{spack_link.resolve()}"')
            projs = [p for p in root.projects() if root.env_views(env_name, p).exists()]
            if projs:
                pstr = ", ".join(f'"{p}"' for p in projs)
                lines.append(f"projects = [{pstr}]")
            lines.append("")

    return "\n".join(lines)


# ── .envrc templates ──────────────────────────────────────────────────────────


def _project_envrc() -> str:
    return """\
# panopoly project-level direnv — discovers context from filesystem.
_P_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
export PANOPOLY_PROJECT="$(basename "$_P_DIR")"

PANOPOLY_WORKTREES=""
for _d in "$_P_DIR/src"/*/; do
    [ -d "$_d" ] || continue
    _n="$(basename "${_d%/}")"
    _p="${_d%/}"
    _var="PANOPOLY_WORKTREE_$(printf '%s' "$_n" | tr 'a-z-.' 'A-Z__')"
    export "$_var"="$_p"
    PANOPOLY_WORKTREES="${PANOPOLY_WORKTREES:+$PANOPOLY_WORKTREES:}$_p"
done
export PANOPOLY_WORKTREES
unset _P_DIR _d _n _p _var
"""


def _env_envrc() -> str:
    return """\
# panopoly environment-level direnv.
_P_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [ -e "$_P_ENV_DIR/spack" ]; then
    export PANOPOLY_SPACK="$_P_ENV_DIR/spack"
    PATH_add "$PANOPOLY_SPACK/bin"
fi
unset _P_ENV_DIR
"""


def _run_envrc() -> str:
    return """\
# panopoly run-level direnv (env/<env>/run/<proj>/.envrc).
_P_RUN="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
_P_PROJ="$(basename "$_P_RUN")"
_P_ENV="$(cd "$_P_RUN/../.." && pwd)"
_P_ROOT="$(cd "$_P_ENV/../.." && pwd)"

source_env "$_P_ENV/.envrc"
source_env "$_P_ROOT/project/$_P_PROJ/.envrc"

export PANOPOLY_PREFIX="$_P_ENV/views/$_P_PROJ"
load_prefix "$PANOPOLY_PREFIX"

unset _P_RUN _P_PROJ _P_ENV _P_ROOT
"""


# ── helpers ───────────────────────────────────────────────────────────────────


def _branch_exists(bare_repo: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(bare_repo), "branch", "--list", branch],
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(result.stdout.strip())


def _add_worktree(
    bare: Path,
    dest: Path,
    branch: Optional[str],
    ref: Optional[str],
) -> None:
    """Add a git worktree at dest, creating the branch if needed."""
    if branch is None:
        effective_branch = _default_branch(bare)
        log.info("adding worktree %s (branch %s)", dest, effective_branch)
        subprocess.run(
            ["git", "-C", str(bare), "worktree", "add", str(dest), effective_branch],
            check=True,
        )
    elif _branch_exists(bare, branch):
        log.info("adding worktree %s (existing branch %s)", dest, branch)
        subprocess.run(
            ["git", "-C", str(bare), "worktree", "add", str(dest), branch],
            check=True,
        )
    else:
        start = ref or _default_branch(bare)
        log.info("adding worktree %s (new branch %s from %s)", dest, branch, start)
        subprocess.run(
            ["git", "-C", str(bare), "worktree", "add", "-b", branch, str(dest), start],
            check=True,
        )


def _repo_name_from_url(giturl: str) -> str:
    """Derive a bare-repo name from a git URL (strip trailing slash and .git)."""
    name = giturl.rstrip("/").rsplit("/", 1)[-1]
    return name.removesuffix(".git")


def _default_branch(bare_repo: Path) -> str:
    """Return the symbolic HEAD branch name of a bare repo."""
    result = subprocess.run(
        ["git", "-C", str(bare_repo), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip() or "main"


def _worktree_branch(worktree: Path) -> str:
    """Return the current branch of a worktree, or short hash if HEAD is detached."""
    result = subprocess.run(
        ["git", "-C", str(worktree), "branch", "--show-current"],
        capture_output=True,
        text=True,
    )
    branch = result.stdout.strip() if result.returncode == 0 else ""
    if branch:
        return branch
    # Detached HEAD — fall back to short commit hash
    result2 = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result2.stdout.strip() if result2.returncode == 0 else "unknown"


def _get_remote_url(bare_repo: Path) -> Optional[str]:
    result = subprocess.run(
        ["git", "-C", str(bare_repo), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None
