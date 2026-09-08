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

from __future__ import annotations

import os
import tomllib
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path, PurePosixPath

import pathspec

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

    Globs match the root-relative POSIX path via pathspec's gitwildmatch
    dialect (T-4102), so `"tests/fixtures/**"` excludes everything under
    that directory.
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


# frob:ticket T-4102
# frob:tests \
# tests/unit/gates/test_ffi_boundary_path_shape.py::test_windows_shaped_rel_path_mechan\
# ism
@lru_cache(maxsize=None)
def _compiled_globs(exclude_globs: tuple[str, ...]) -> pathspec.PathSpec:
    """Compile `exclude_globs` under gitwildmatch semantics (cached per tuple).

    T-4102: `is_excluded` previously matched via `fnmatch.fnmatch`, which
    (like T-4013's identical finding in `frob.policy`) runs BOTH operands
    through `os.path.normcase` -- on Windows that turns a glob's forward
    slashes into backslashes, so a POSIX-shaped glob accidentally matches a
    backslash-joined path, and the same (rel, glob) pair can answer
    differently per platform. `pathspec`'s `gitwildmatch` dialect (already a
    direct runtime dependency, T-4013) is platform-independent and has no
    normcase step.
    """
    return pathspec.PathSpec.from_lines("gitignore", list(exclude_globs))


# frob:doc docs/modules/app.md#shared-exclude-glob-logic
# frob:waive AFFECT001 reason="T-4102 only swaps is_excluded's internal matcher from \
# fnmatch.fnmatch to pathspec gitwildmatch (a platform- dependence bugfix with no \
# Linux-visible behavior change for the POSIX- shaped rel paths every producer emits); \
# docs/modules/app.md's own description ('True if rel_path matches one of the globs') \
# already describes the contract, not the matcher, and stays accurate unchanged"
# frob:ticket T-4155
# frob:tests \
# tests/unit/gates/test_ffi_boundary_path_shape.py::test_windows_shaped_rel_path_mechan\
# ism
def is_excluded(rel_path: str, exclude_globs: tuple[str, ...]) -> bool:
    """True if `rel_path` matches any glob, identically on every platform.

    T-4155: `pathspec.PathSpec.match_file` derives ITS separator-normalization
    set from the host OS (`os.sep`/`os.altsep`) when none is given, so a
    backslash in `rel_path` was an ordinary filename character on posix but
    got rewritten to `/` on Windows -- the same (rel, glob) pair answered
    differently per platform, the identical class of bug T-4102 fixed for
    case-folding one layer down in fnmatch. We pin `separators=("\\\\",)`
    explicitly so a backslash is ALWAYS folded to `/` before matching,
    regardless of host: every in-repo producer already emits POSIX-relative
    paths (T-3941/T-3947/T-3948/T-4107), so this only matters for the
    boundary case, and normalizing there makes `is_excluded` robust against
    a future producer regressing on this exact axis instead of merely
    matching today's inputs.
    """
    if not exclude_globs:
        return False
    return _compiled_globs(exclude_globs).match_file(rel_path, separators=("\\",))


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
    `"prefix/**"` and gitwildmatch's `**` requires a path component after
    the `/` to match -- it does not match `prefix` itself), and nested git
    checkouts (`_is_nested_worktree`).
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
