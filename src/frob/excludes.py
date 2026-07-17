"""The one place that reads `[graph] exclude` from frob.toml.

Every file-walking surface -- the graph build AND the standalone
`frob dup`/`frob arch`/`frob cycle` scanners -- consults these so a repo
declares its generated/vendored dirs once and every tool respects it
(T-0026: the scanners used to walk node_modules/worktrees the graph had
excluded). A second copy of this logic is exactly the desync frob exists
to prevent, so it lives here as a leaf with no frob dependencies.
"""

from __future__ import annotations

import fnmatch
import tomllib
from pathlib import Path

from frob.logging import get_logger

_log = get_logger(__name__)

# Always-pruned directory names, additive to the frob.toml globs.
BUILTIN_SKIP_DIRS = frozenset(
    {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "target",
        "build",
        "dist",
        ".frob",
        ".worktrees",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
)


def load_exclude_globs(root: Path) -> tuple[str, ...]:
    """Read `[graph] exclude = [...]` from frob.toml; absent config is `()`.

    Globs match the root-relative POSIX path via fnmatch, so
    `"tests/fixtures/**"` excludes everything under that directory.
    """
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return ()
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("excludes: could not parse %s: %s", toml_path, exc)
        return ()
    globs = doc.get("graph", {}).get("exclude", [])
    if not isinstance(globs, list) or not all(isinstance(g, str) for g in globs):
        _log.warning("excludes: [graph].exclude must be a list of strings")
        return ()
    return tuple(globs)


def is_excluded(rel_path: str, exclude_globs: tuple[str, ...]) -> bool:
    """True if `rel_path` (root-relative, POSIX) matches any glob."""
    return any(fnmatch.fnmatch(rel_path, glob) for glob in exclude_globs)


def is_skipped_dir(name: str) -> bool:
    """True for a directory name that is always pruned (built-in skip set)."""
    return name in BUILTIN_SKIP_DIRS or name.endswith(".egg-info")


__all__ = [
    "BUILTIN_SKIP_DIRS",
    "is_excluded",
    "is_skipped_dir",
    "load_exclude_globs",
]
