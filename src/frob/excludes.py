"""The one place that reads `[graph] exclude` from frob.toml.

Every file-walking surface -- the graph build AND the standalone
`frob dup`/`frob arch`/`frob cycle` scanners -- consults these so a repo
declares its generated/vendored dirs once and every tool respects it
(T-0026: the scanners used to walk node_modules/worktrees the graph had
excluded). A second copy of this logic is exactly the desync frob exists
to prevent, so it lives here as a near-leaf module -- its only frob
dependency is `frob.gitio.run_argv` (T-0471's `iter_files` git-ls-files
fast path), itself a leaf with no further frob imports.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: src/frob/excludes.py's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import fnmatch
import os
import tomllib
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

from frob.gitio import run_argv
from frob.logging import get_logger

_log = get_logger(__name__)

# Always-pruned directory names, additive to the frob.toml globs.
# frob:doc docs/modules/app.md#shared-exclude-glob-logic
# frob:ticket T-0410
# T-0410 perf audit finding M6: `.hypothesis` (Hypothesis's example/
# constants DB) and `.serena` (Serena MCP's cache dir) were both missing
# here -- neither has a tree-sitter grammar so nothing gets misparsed as
# source, but every rglob-based stage still stat's/opens/`is_test_file`-
# checks each of their entries (measured: 1298 `.hypothesis/constants` +
# 44 `.hypothesis/examples` + `.serena/cache` files walked, wastefully, by
# every stage in this checkout). One-line, zero-risk fix.
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
        ".claude",
        ".worktrees",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".hypothesis",
        ".serena",
    }
)


# frob:doc docs/modules/app.md#shared-exclude-glob-logic
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


# frob:doc docs/modules/app.md#shared-exclude-glob-logic
def is_excluded(rel_path: str, exclude_globs: tuple[str, ...]) -> bool:
    """True if `rel_path` (root-relative, POSIX) matches any glob."""
    return any(fnmatch.fnmatch(rel_path, glob) for glob in exclude_globs)


# frob:doc docs/modules/app.md#shared-exclude-glob-logic
def is_skipped_dir(name: str) -> bool:
    """True for a directory name that is always pruned (built-in skip set)."""
    return name in BUILTIN_SKIP_DIRS or name.endswith(".egg-info")


# frob:ticket T-0239
# frob:tests tests/test_excludes.py::test_is_nested_worktree_detects_own_git_dir
# frob:tests tests/test_excludes.py::test_is_nested_worktree_git_file_form
# frob:tests tests/test_excludes.py::test_is_nested_worktree_false_for_root_itself
# frob:tests tests/test_excludes.py::test_is_nested_worktree_false_for_plain_subdir
def _is_nested_worktree(dir_path: Path, root: Path) -> bool:
    """True if `dir_path` is its own git checkout (has a `.git` entry) other
    than `root` itself.

    Gitignored nested checkouts (`.claude/worktrees/agent-*`) are a real git
    worktree per agent dispatch and are almost always excluded via
    `[graph] exclude`, but a repo that forgets the glob (or a checkout parked
    somewhere the glob doesn't cover) would otherwise still be walked and
    parsed wholesale -- T-0239 measured this as ~73pct of a `frob check` run
    spent re-parsing stale sibling worktrees. `.git` presence is a strictly
    stronger, config-independent signal than any glob, so it is checked
    unconditionally rather than relying on exclude globs alone.
    """
    return dir_path != root and (dir_path / ".git").exists()


# frob:ticket T-0239
# frob:tests tests/test_excludes.py::test_should_prune_dir_covers_all_three_signals
def _should_prune_dir(
    dir_path: Path, root: Path, exclude_globs: tuple[str, ...] = ()
) -> bool:
    """True if `dir_path` should be pruned BEFORE it is descended into.

    Combines all three exclusion signals a walker needs to check prior to
    recursing (not after collecting files from inside it, which is the bug
    T-0239 fixed -- filtering files post-walk still pays the full os.walk
    cost of every excluded subtree): the built-in skip-name set
    (`is_skipped_dir`), the repo's `[graph] exclude` globs (`is_excluded`,
    probed with a synthetic child path since the globs are typically
    `"prefix/**"` and fnmatch requires trailing characters after the `/` to
    match), and nested git checkouts (`_is_nested_worktree`).
    """
    if is_skipped_dir(dir_path.name):
        return True
    if _is_nested_worktree(dir_path, root):
        return True
    if exclude_globs:
        rel = dir_path.relative_to(root).as_posix()
        if is_excluded(rel, exclude_globs) or is_excluded(f"{rel}/.", exclude_globs):
            return True
    return False


# frob:doc docs/modules/app.md#shared-exclude-glob-logic
# frob:tests tests/test_excludes.py::test_is_test_file_by_dir_component
# frob:tests tests/test_excludes.py::test_is_test_file_by_name_prefix_suffix
# frob:tests tests/test_excludes.py::test_is_test_file_typescript_naming
# frob:tests tests/test_excludes.py::test_is_test_file_false_for_production_module
def is_test_file(path: str) -> bool:
    """True if `path` is itself a test file, by a `tests/` directory component
    or by a test-file naming convention across Python and TS/JS.

    The single home for the "is this a test file" predicate: the arch gate,
    the gates coverage/design checks, and the touched-set selector all need
    the SAME heuristic, and three drifting private copies (Python-only in
    two of them, TS-aware in the third) were exactly the desync this module
    exists to prevent. Covers `test_*.py`/`*_test.py` and `*.test.ts`/
    `*_test.tsx`-style names so TS/JS test files are recognized too.
    """
    pure = PurePosixPath(path)
    if "tests" in pure.parts[:-1]:
        return True
    name = pure.stem
    return (
        name.startswith("test_")
        or name.endswith("_test")
        or ".test" in pure.name
        or "_test." in pure.name
    )


# frob:doc docs/modules/app.md#shared-exclude-glob-logic
# frob:ticket T-0471
# frob:tests tests/test_excludes.py::test_walk_pruned_does_not_descend_venv_or_git
def walk_pruned(root: Path, *, exclude_globs: tuple[str, ...] = ()) -> Iterator[Path]:
    """Yield every file under `root`, pruning `_should_prune_dir` directories
    IN PLACE before `os.walk` descends into them.

    The os.walk-prune fallback half of T-0471's shared walk primitive
    (`iter_files` prefers the `git ls-files` fast path and only falls back to
    this): unlike `root.rglob("*")` -- which cannot be pruned mid-walk and so
    always pays the full traversal cost of `.git`/`.venv`/`node_modules`/
    `.claude/worktrees`/build output before any post-hoc filter runs (the
    T-0239 bug class, and the mistake `frob.gates._walk_lint`'s WALK001 now
    makes a static check) -- `dirnames[:]` mutation here means a pruned
    subtree is never entered at all.
    """
    if not exclude_globs:
        exclude_globs = load_exclude_globs(root)
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [
            name
            for name in dirnames
            if not _should_prune_dir(current / name, root, exclude_globs)
        ]
        for name in filenames:
            yield current / name


# frob:doc docs/modules/app.md#shared-exclude-glob-logic
# frob:ticket T-0471
# frob:tests tests/test_excludes.py::test_iter_files_git_fast_path_matches_ls_files
# frob:tests tests/test_excludes.py::test_iter_files_suffix_filter
# frob:tests tests/test_excludes.py::test_iter_files_falls_back_to_walk_pruned_outside_git  # noqa: E501
def iter_files(root: Path, *, suffix: str | None = None) -> tuple[Path, ...]:
    """Every file under `root`, pruning the same heavy/irrelevant dirs
    `_should_prune_dir` always prunes -- the ONE shared entry point T-0471's
    WALK001 gate points every raw `Path.rglob`/`os.walk`/`glob.glob("**"...)`
    caller at.

    Prefers a `git ls-files` fast path (tracked files only, no traversal at
    all) when `root` looks like a git work tree; falls back to
    `walk_pruned` otherwise (a non-repo root, or a `git` failure). Both
    paths return root-relative-safe absolute `Path`s. `suffix` (e.g.
    `".py"`) filters the result to that extension, matched case-
    insensitively like the call sites this replaces (`frob.xref`).
    """
    files: tuple[Path, ...]
    if (root / ".git").exists():
        spawned = run_argv(("git", "-C", str(root), "ls-files", "-z"))
        if spawned.is_ok and spawned.danger_ok.returncode == 0:
            raw = spawned.danger_ok.stdout
            files = tuple(root / rel for rel in raw.split("\0") if rel)
            _log.debug("iter_files: git ls-files fast path, %d file(s)", len(files))
        else:
            _log.warning(
                "iter_files: git ls-files failed under %s, falling back to walk_pruned",
                root,
            )
            files = tuple(walk_pruned(root))
    else:
        files = tuple(walk_pruned(root))
    if suffix is not None:
        lowered = suffix.lower()
        files = tuple(f for f in files if f.suffix.lower() == lowered)
    return files


__all__ = [
    "BUILTIN_SKIP_DIRS",
    "is_excluded",
    "is_skipped_dir",
    "is_test_file",
    "iter_files",
    "load_exclude_globs",
    "walk_pruned",
]
