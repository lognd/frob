"""State/disable-check leaf for `frob.app.telemetry` (T-3411).

Extracted from `frob.app.telemetry.__init__` so `_footguns.py` and
`_usage.py` can import `is_disabled`/`_telemetry_path` (and `_footguns`
its `_home_config_state_hash`/`_external_path_arg_hash`) from a genuine
leaf module instead of reaching back into the partially-initialized
package `__init__.py` -- this collapses the `frob.app.telemetry` <->
`_footguns` <-> `_usage` import cycle (T-2694's bottom-of-file ordering
workaround is no longer needed). Every name here is re-exported from
`frob.app.telemetry.__init__` to preserve its public surface.
"""

from __future__ import annotations

import os
from pathlib import Path

# frob:doc docs/guides/agentic-time-profiling.md#public-api
TELEMETRY_REL = Path(".frob") / "telemetry.jsonl"
"""Path (relative to a repo root) telemetry events are appended to."""

_NO_TELEMETRY_ENV = "FROB_NO_TELEMETRY"


# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::test_append_event_respects_no_telemetry_env
# frob:tests \
# tests/test_telemetry.py::test_no_telemetry_env_false_like_values_stay_enabled
def is_disabled() -> bool:
    """True when the operator opted out via `FROB_NO_TELEMETRY` (any
    non-empty, non-`0`/`false` value)."""
    value = os.environ.get(
        _NO_TELEMETRY_ENV, ""
    )  # frob:waive SEC110 reason="opt-out flag, not a secret"
    return value.strip().lower() not in ("", "0", "false")


def _telemetry_path(root: Path) -> Path:
    """Absolute telemetry file path under `root`."""
    return root / TELEMETRY_REL


# frob:ticket T-2191
_HOME_CLAUDE_RUNTIME_STATE_DIRS = frozenset(
    {
        # frob:ticket T-2191
        # Claude Code's own well-known RUNTIME/session-state directories
        # under `~/.claude` -- churn on every turn of every session
        # (transcripts, shell snapshots, IDE state, todo scratch, usage
        # telemetry) regardless of whether any `frob` verb read or wrote
        # anything. Excluded by NAME, not by full path, so this stays
        # correct across machines with a differently-cased/located home.
        # This is a small, stable list of Claude Code's OWN reserved
        # directory names (documented, product-level, changes on the
        # order of Claude Code releases) -- a fundamentally different,
        # far more durable kind of list than "which frob subcommands
        # read outside the repo" (which is exactly what this ticket's
        # acceptance criteria forbid hardcoding): this list exists to
        # exclude noise, not to include coverage, so a missed entry only
        # ever makes the digest MORE sensitive (a false "changed"), never
        # a false "unchanged" the way an exempt-subcommand list would.
        "projects",
        "todos",
        "shell-snapshots",
        "logs",
        "ide",
        "statsig",
        "history",
        "__pycache__",
    }
)


# frob:ticket T-2322
# frob:ticket T-2303
# frob:invariant terminates reason="recurses only into a DIRECT child directory entry \
# (entry.is_dir()) returned by os.scandir(root) -- the filesystem directory tree \
# rooted at home_claude is finite depth (no directory can be its own descendant \
# outside a symlink cycle, and this walk never follows symlinks: entry.is_dir/is_file \
# both pass follow_symlinks=False), so every recursive call strictly descends one real \
# directory level toward that finite floor" measure="depth of the home_claude \
# directory subtree strictly decreases with each recursive call"
def _walk_home_claude_entries(root: Path, home_claude: Path) -> list[str]:
    """Recursive part of `_home_config_state_hash` (T-2322 ARCH001 split,
    zero behavior change): returns `"relpath:size:mtime_ns"` entries for
    every regular file under `root`, pruning `_HOME_CLAUDE_RUNTIME_STATE_
    DIRS` only at `home_claude`'s own top level (matching the original
    inline closure's `root == home_claude` check) -- `home_claude` is
    threaded through explicitly since this is no longer a closure over
    the caller's local variable. Best-effort: an unreadable directory
    entry is skipped, never raised."""
    out: list[str] = []
    try:
        with os.scandir(root) as it:
            children = sorted(it, key=lambda e: e.name)
    except OSError:
        return out
    for entry in children:
        if entry.is_dir(follow_symlinks=False):
            if root == home_claude and entry.name in _HOME_CLAUDE_RUNTIME_STATE_DIRS:
                continue
            out.extend(_walk_home_claude_entries(Path(entry.path), home_claude))
        elif entry.is_file(follow_symlinks=False):
            try:
                stat = entry.stat()
            except OSError:
                continue
            rel = Path(entry.path).relative_to(home_claude)
            out.append(f"{rel}:{stat.st_size}:{stat.st_mtime_ns}")
    return out


# frob:ticket T-2191
# frob:tests tests/test_telemetry.py::test_redundant_rerun_not_flagged_when_home_claude_config_changed  # noqa: E501
# frob:tests tests/test_telemetry.py::test_redundant_rerun_still_flags_when_nothing_changed_at_all  # noqa: E501
def _home_config_state_hash() -> str:
    """sha256-derived digest (first 12 hex chars) over every regular
    file's `(relpath, size, mtime_ns)` under `~/.claude`, excluding
    Claude Code's own known runtime/session-state subdirectories
    (`_HOME_CLAUDE_RUNTIME_STATE_DIRS`) -- T-2191.

    T-1360's `REDUNDANT_RERUN` used to key SOLELY on `(subcommand,
    args_head, tree_hash)`, where `tree_hash` covers the REPO tree only --
    correct for a verb whose result depends only on repo state, wrong for
    one that also reads/writes `~/.claude` (this repo's one existing
    out-of-repo materialized-copy target: `frob claude sync`'s
    destination, per `.claude/hooks/sync-claude-config.py`'s own
    docstring). Reproduced live: `claude sync --check` reported drifted,
    `claude sync` wrote `~/.claude/refs/*`, and the next `--check` claimed
    "nothing has changed since" -- false, because `~/.claude` had.

    Folding this digest into the redundancy key (alongside `tree_hash`,
    never replacing it) makes the check correct for `frob claude sync`
    AND for any future verb that happens to read/write under the same
    directory, without maintaining a hardcoded list of exempt subcommand
    names -- the fix generalizes by WHERE a verb's out-of-repo input
    lives, not by WHICH verb it is. A verb with a genuinely different
    out-of-repo input (not under `~/.claude`) is not covered by this
    digest -- see this function's own limits noted in `_tip_redundant_
    rerun`'s docstring.

    Returns `"none"` when `~/.claude` does not exist (nothing to be blind
    to), `"unreadable"` on any OSError walking it (never raises -- matches
    `tree_hash`'s own best-effort "unknown" convention: a digest that
    cannot be computed must never silently read as "unchanged")."""
    import hashlib

    # frob:waive WALK001 reason="~/.claude is the user's home config dir, not the repo \
    # tree -- no .git/.venv/node_modules/build/dist/target to prune, and \
    # frob.excludes' repo-relative exclude globs do not apply outside a project \
    # checkout (same rationale as the vet/_source.py WALK001 waivers for a \
    # home-directory cache root); the runtime-state subdirs this function itself needs \
    # to skip are pruned explicitly below via _HOME_CLAUDE_RUNTIME_STATE_DIRS, not via \
    # frob.excludes"
    home_claude = Path.home() / ".claude"
    if not home_claude.is_dir():
        return "none"

    try:
        entries = sorted(_walk_home_claude_entries(home_claude, home_claude))
    except OSError:
        return "unreadable"
    digest = hashlib.sha256("\n".join(entries).encode("utf-8", errors="replace"))
    return digest.hexdigest()[:12]


# frob:ticket T-2204
_EXTERNAL_PATH_EXCLUDE_DIRS = frozenset(
    {
        # frob:ticket T-2204
        # Generic, non-repo-specific churn dirs to prune while walking an
        # ARBITRARY external path argument (a fixture tree, a sibling
        # checkout, ...) -- unlike `_HOME_CLAUDE_RUNTIME_STATE_DIRS`, this
        # is not "known runtime state under one well-known directory", it
        # is "names common enough to be noise wherever they appear", so a
        # missed entry only ever makes the digest MORE sensitive (a false
        # "changed"), never a false "unchanged" -- same asymmetry
        # `_home_config_state_hash`'s own list already leans on.
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "dist",
        "build",
        "target",
    }
)


# frob:ticket T-2204
def _looks_like_path_token(token: str) -> bool:
    """`True` if `token` (one whitespace-split piece of a redacted
    `args_head`) is plausibly a filesystem path argument rather than a
    flag, subcommand word, or bare value -- a path SEPARATOR is the
    strongest signal (`frob cycle some/fixture/dir`), and an otherwise
    bare token that happens to exist on disk relative to the current
    working directory (`frob cycle srclayout` run from inside the
    fixture's own parent) is the fallback. Deliberately permissive: a
    false positive here only adds a harmless extra digest input, while a
    false negative reproduces this ticket's own bug (a real external
    input silently uncovered)."""
    if not token or token.startswith("-"):
        return False
    if "/" in token or "\\" in token:
        return True
    try:
        return Path(token).exists()
    except OSError:
        return False


# frob:ticket T-2204
def _walk_external_path_state(path: Path) -> list[str]:
    """`(relpath-from-`path`, size, mtime_ns)` for every regular file
    under `path` (pruning `_EXTERNAL_PATH_EXCLUDE_DIRS` by name), or a
    single `f"{path}:{size}:{mtime_ns}"` entry when `path` is itself a
    file, or `[f\"MISSING:{path}\"]` when `path` does not exist at all --
    the MISSING sentinel is exactly what makes a deleted fixture register
    as a state CHANGE (T-2204's own measured bug) rather than silently
    matching whatever state existed when the path was last present.
    Never raises; an unreadable entry is simply skipped."""
    if not path.exists():
        return [f"MISSING:{path}"]
    if path.is_file():
        try:
            stat = path.stat()
        except OSError:
            return [f"UNREADABLE:{path}"]
        return [f"{path}:{stat.st_size}:{stat.st_mtime_ns}"]

    out: list[str] = []

    def _walk(root: Path) -> None:
        try:
            with os.scandir(root) as it:
                children = sorted(it, key=lambda e: e.name)
        except OSError:
            return
        for entry in children:
            if entry.is_dir(follow_symlinks=False):
                if entry.name in _EXTERNAL_PATH_EXCLUDE_DIRS:
                    continue
                _walk(Path(entry.path))
            elif entry.is_file(follow_symlinks=False):
                try:
                    stat = entry.stat()
                except OSError:
                    continue
                rel = Path(entry.path).relative_to(path)
                out.append(f"{rel}:{stat.st_size}:{stat.st_mtime_ns}")

    _walk(path)
    return out


# frob:ticket T-2204
# frob:tests tests/test_telemetry.py::TestExternalPathArgHash.test_a_deleted_external_fixture_changes_the_hash  # noqa: E501
# frob:tests tests/test_telemetry.py::TestExternalPathArgHash.test_no_path_looking_argument_yields_none  # noqa: E501
def _external_path_arg_hash(root: Path, args_head: str) -> str:
    """sha256-derived digest (first 12 hex chars) over the on-disk state of
    every positional-PATH-shaped token in `args_head` that resolves
    OUTSIDE `root` -- the generic fix T-2204 asks for: `REDUNDANT_RERUN`'s
    key used to cover `root`'s own tree (`tree_hash`) and one hardcoded
    out-of-repo location (`~/.claude`, `_home_config_state_hash`), but any
    verb taking an arbitrary positional PATH argument (`frob cycle`,
    `outline`, `map`, ...) decides from a tree neither digest describes.
    Measured live: `frob cycle <fixture>/srclayout` reported a cycle,
    deleting that fixture's `pyproject.toml` flipped the verdict to `no
    cycles found`, and the unchanged `tree_hash`/`home_config_hash` pair
    made `REDUNDANT_RERUN` claim nothing had changed -- false.

    Derives coverage from WHAT THE ARGS NAME, not from a hardcoded list of
    known external locations (matching `_home_config_state_hash`'s own
    "generalize by WHERE state lives" precedent, extended from one fixed
    location to arbitrary caller-supplied ones): each whitespace-split
    token in `args_head` that `_looks_like_path_token` accepts is resolved
    against the current working directory, and any that resolves to a
    location NOT under `root` (already covered by `tree_hash`) has its
    on-disk state folded in via `_walk_external_path_state` -- including a
    MISSING sentinel when the path no longer exists, which is exactly the
    delete-the-fixture case this ticket measured.

    Returns `"none"` when no token in `args_head` resolves to an external
    path at all (nothing to be blind to, matching `_home_config_state_
    hash`'s own convention for "not applicable" runs) -- the common case
    for a subcommand with no PATH-shaped positional argument. Never
    raises; an individual token's own resolution failure is skipped, not
    fatal to the whole digest."""
    import hashlib

    try:
        root_resolved = root.resolve()
    except OSError:
        root_resolved = root

    cwd = Path.cwd()
    entries: list[str] = []
    for token in args_head.split():
        if not _looks_like_path_token(token):
            continue
        candidate = Path(token)
        try:
            # frob:waive PERF008 reason="T-2303: candidate is THIS iteration's own \
            # token (a different path every time args_head.split() advances) -- cwd is \
            # the only genuinely loop-invariant operand here, and it is already \
            # computed once above the loop; there is nothing loop-invariant left to \
            # hoist, the same shape already accepted for _land_cmd.py:2361/1321 and \
            # _rapid_sweep.py:2411 (T-2321/T-1841)"
            resolved = (
                candidate if candidate.is_absolute() else cwd / candidate
            ).resolve()
        except OSError:
            continue
        try:
            resolved.relative_to(root_resolved)
            continue  # inside the repo tree -- already covered by tree_hash
        except ValueError:
            pass
        entries.extend(_walk_external_path_state(resolved))

    if not entries:
        return "none"
    digest = hashlib.sha256(
        "\n".join(sorted(entries)).encode("utf-8", errors="replace")
    )
    return digest.hexdigest()[:12]

