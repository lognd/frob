"""Non-gated agentic time/token telemetry stream (T-0178) -- event
recording, the write path every `frob` subcommand's telemetry hook goes
through.

Diagnostics ONLY: no rule ids here, nothing in this module fails a gate or
is consulted by `frob check`. Every `frob` CLI invocation and every ticket
state transition appends one JSON line to `.frob/telemetry.jsonl`, local
only (`.frob/` is gitignored, never networked). Set `FROB_NO_TELEMETRY=1`
to opt out entirely -- `is_disabled()` is the single source of truth every
call site in this module checks before writing anything.

Redaction discipline: any free-text field that might carry a copy-pasted
secret (a command's argv head, a tool-call snippet) is passed through
`redact_command`, which reuses `frob.security._redact`'s provider patterns
(T-0157, extracted out of `frob.gates._secrets` into that lightweight,
`frob.gates`-independent module by T-1318 so this module's per-invocation
redaction call never drags in the whole `frob.gates` aggregator package)
rather than re-deriving a second scanner -- two secret scanners is exactly
the kind of drift-prone duplication the engineering principles forbid.

T-2694 (T-1656 LARGE001 successor): this used to be one 1148-line
`telemetry.py` bundling three genuinely distinct, separately-consumed
concerns. Now a package of three: THIS file (event recording -- the
write path), `_footguns.py` (post-command advisory tips, a distinct
read-then-render concern with its own opt-out env var), and `_usage.py`
(corpus-wide aggregate reporting for `frob doctor usage`-style
consumers, read-only over the event stream this file writes). Every
public name from all three is re-exported here unchanged so none of the
14 pre-existing `from frob.app.telemetry import ...` call sites need
editing (same import-compatibility precedent T-1089's `ticket_runner`
split and T-1656's own prior telemetry split already established)."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from frob.logging import get_logger

_log = get_logger(__name__)
# frob:doc docs/guides/agentic-time-profiling.md#public-api
TELEMETRY_REL = Path(".frob") / "telemetry.jsonl"
"""Path (relative to a repo root) telemetry events are appended to."""

_NO_TELEMETRY_ENV = "FROB_NO_TELEMETRY"

# frob:doc docs/guides/agentic-time-profiling.md#public-api
T = TypeVar("T")
"""Generic return type `timed_call` preserves from the wrapped callable."""


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


# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::test_iso_now_has_iso_shape_with_z_suffix
def iso_now() -> str:
    """Current UTC time as an ISO-8601 timestamp with a `Z` suffix -- the
    single timestamp format every telemetry record and ticket-transition
    event in this module uses, so downstream aggregation never has to
    reconcile two shapes."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:invariant INV-022
# invariant spec: [INV-022](invariants/INV-022.md)
# frob:tests tests/test_telemetry.py::test_redact_command_hides_recognizable_secret
# frob:tests tests/test_telemetry.py::test_redact_command_leaves_ordinary_text_alone
def redact_command(text: str) -> str:
    """`text` with any recognizable provider-secret substring replaced by
    `frob.gates._secrets`'s fixed-shape placeholder (T-0157 reuse).
    Applied to every free-text field a telemetry record stores before it is
    written -- a leaked scanner is worse than no scanner.

    Reuses `frob.gates._secrets`'s own single-line scanner (`_scan_line`)
    and per-token redactor (`_redact`) rather than re-deriving a second
    scanner -- both are private (`frob.gates._secrets` exposes no public
    whole-string redactor), but same-repo private-module reuse is an
    established pattern here (e.g. `frob.strata._effects` importing
    `frob.vet._capability._PATTERNS` directly). `_scan_line` takes a line
    list plus an index (it also checks the line above for a
    `frob:secret-fake` marker); telemetry text is always a single line, so
    it is wrapped as `[text]` at index 0. `_scan_line` returns `(pattern,
    token)` pairs, not spans, so replacement is a plain `str.replace` per
    matched token -- correct here because a real-looking secret token is
    long/high-entropy enough that an incidental second occurrence in the
    same short command-line string is not a realistic concern, unlike a
    full source file where `_secrets.py`'s own span-tracking matters.

    T-1318: imports from `frob.security._redact`, NOT `frob.gates._secrets`
    -- `frob.gates._secrets` is a submodule of the heavy `frob.gates`
    aggregator package, and importing ANY submodule of a package always
    executes that package's own `__init__.py` first (ordinary Python
    import semantics), which eagerly imports `frob.gates`'s entire stage
    roster as a side effect. Since `timed_call`'s `finally` block calls
    `record_cli_event` -> `redact_command` on EVERY CLI invocation
    regardless of subcommand, that import used to cost ~257ms on every
    single `frob` command -- see `frob.security._redact`'s own module
    docstring for the extraction this fixes.
    """
    from frob.security._redact import _redact, _scan_line

    out = text
    for pattern, token in _scan_line([text], 0):
        out = out.replace(token, _redact(token, pattern.display_prefix))
    return out


def _telemetry_path(root: Path) -> Path:
    """Absolute telemetry file path under `root`."""
    return root / TELEMETRY_REL


# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::test_append_event_writes_one_json_line
# frob:tests tests/test_telemetry.py::test_append_event_swallows_oserror_and_logs
def append_event(root: Path, record: Mapping[str, Any]) -> None:
    """Append one JSON-line `record` to `root`'s telemetry stream.

    Best-effort and never gate-affecting: any I/O failure is logged at
    debug and swallowed, never raised, since telemetry must never be able
    to break a real `frob` invocation. A no-op entirely when
    `is_disabled()`.
    """
    if is_disabled():
        return
    path = _telemetry_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(record), sort_keys=True))
            fh.write("\n")
    except OSError as exc:
        _log.debug("telemetry: append failed (ignored): %s", exc)


# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::test_tree_hash_returns_stripped_stdout_on_success  # noqa: E501
# frob:tests tests/test_telemetry.py::test_tree_hash_returns_unknown_on_nonzero_returncode  # noqa: E501
# frob:tests tests/test_telemetry.py::test_tree_hash_returns_unknown_when_git_spawn_errors  # noqa: E501
def tree_hash(root: Path) -> str:
    """Short git HEAD sha for `root`, or `\"unknown\"` if git is unavailable
    -- lets retread detection (identical command + tree_hash re-runs) tell
    a cache-hit candidate apart from a run against genuinely changed code."""
    from frob.gitio import run_argv

    spawned = run_argv(
        ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
        cwd=root,
        timeout_s=10.0,
    )
    if spawned.is_err:
        return "unknown"
    result = spawned.danger_ok
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


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


# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::test_estimate_tokens_is_len_over_four
def estimate_tokens(text: str) -> int:
    """Rough `len(text) / 4` token estimate -- the documented heuristic
    method (T-0178 addendum a); cheap and good enough to rank tools by
    cumulative output size, not intended as an exact tokenizer count."""
    return max(0, len(text) // 4)


# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::test_record_cli_event_shape
def record_cli_event(
    root: Path,
    *,
    subcommand: str,
    args_head: str,
    duration_ms: float,
    exit_code: int,
) -> None:
    """Append one `kind=\"cli\"` event for a completed `frob` invocation.

    Runs under `frob.logging.quiet.quiet_stdout_logs()` -- `tree_hash`
    spawns `git` via `frob.gitio.run_argv`, which logs at INFO/DEBUG (the
    stdout handler's default level per `config.toml`). Without muting it,
    that log line prints AFTER whatever the command itself already wrote
    to stdout, silently corrupting any `--json` command's output for a
    caller doing `json.loads(stdout)` -- telemetry must be invisible on
    stdout, full stop.
    """
    from frob.logging.quiet import quiet_stdout_logs

    with quiet_stdout_logs():
        record = {
            "iso_ts": iso_now(),
            "kind": "cli",
            "subcommand": subcommand,
            "args_head": redact_command(args_head),
            "duration_ms": round(duration_ms, 3),
            "exit": exit_code,
            "tree_hash": tree_hash(root),
            # frob:ticket T-2191
            "home_config_hash": _home_config_state_hash(),
            # frob:ticket T-2204
            "external_path_hash": _external_path_arg_hash(root, args_head),
        }
        append_event(root, record)


# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::test_record_ticket_event_shape
# frob:tests tests/test_telemetry.py::test_record_ticket_event_merges_extra_fields  # noqa: E501
def record_ticket_event(
    root: Path, *, ticket_id: str, event: str, extra: Mapping[str, Any] | None = None
) -> None:
    """Append one `kind=\"ticket\"` state-transition event with an ISO
    timestamp -- `created`/`started`/`done` are date-only on the `Ticket`
    frontmatter itself, so per-ticket cycle time is only computable by
    reconstructing it from this stream (T-0178 deliverable 2)."""
    record: dict[str, Any] = {
        "iso_ts": iso_now(),
        "kind": "ticket",
        "ticket_id": ticket_id,
        "event": event,
    }
    if extra:
        record.update(extra)
    append_event(root, record)


# frob:ticket T-1724
# frob:ticket T-1787
# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::TestRecordDispatchEvent.test_start_and_end_events_shaped_correctly  # noqa: E501
# frob:tests tests/test_telemetry.py::TestRecordDispatchEvent.test_optional_fields_omitted_when_none  # noqa: E501
def record_dispatch_event(
    root: Path,
    *,
    dispatch_id: str,
    event: str,
    worktree: str | None = None,
    branch: str | None = None,
    cold_start: bool | None = None,
) -> None:
    """Append one `kind=\"dispatch\"` boundary event -- `event="start"` when
    an agent begins work in a worktree, `event="end"` when it stops (T-1724).
    `frob.stats._agentic.dispatch_cost_report` joins the pair on
    `dispatch_id` and attributes `kind="tool"`/`kind="ticket"` events whose
    `iso_ts` falls between them to that dispatch, so cost (tokens, tool
    calls, wall clock) can finally be measured against delivery (tickets
    landed) per dispatch instead of hand-tallied from notification text.

    `cold_start` is the field this ticket exists for: PASS IT EXPLICITLY at
    `event="start"` time (`True` for a fresh agent, `False` for a resumed
    one) rather than leaving the reader to infer it from whether some other
    counter went up -- that ambiguity is exactly what produced the
    2026-08-07 published-then-withdrawn retirement threshold. `None` means
    "not recorded" (an older caller, or a caller that genuinely could not
    tell) and must never be silently treated as either `True` or `False`
    downstream.

    Called by `.claude/hooks/dispatch-telemetry.py` (T-1787) at
    `SessionStart` (`event="start"`) and `Stop` (`event="end"`) -- the
    Claude Code hook wiring T-1724 deliberately left out of its own scope
    (schema + join only)."""
    record: dict[str, Any] = {
        "iso_ts": iso_now(),
        "kind": "dispatch",
        "dispatch_id": dispatch_id,
        "event": event,
    }
    if worktree is not None:
        record["worktree"] = worktree
    if branch is not None:
        record["branch"] = branch
    if cold_start is not None:
        record["cold_start"] = cold_start
    append_event(root, record)


def _exit_code_from_system_exit(exc: SystemExit) -> int:
    """Map a caught `SystemExit` to a telemetry exit code: `sys.exit()`/
    `sys.exit(None)` is conventionally SUCCESS (0); an int code is used
    as-is; anything else (e.g. a message string) is treated as non-zero,
    matching Python's own `SystemExit` convention."""
    if exc.code is None:
        return 0
    if isinstance(exc.code, int):
        return exc.code
    return 1


def _finish_timed_call(
    root: Path,
    *,
    subcommand: str,
    args_head: str,
    duration_ms: float,
    exit_code: int,
) -> None:
    """`timed_call`'s `finally`-block work: record the CLI event, then run
    footgun detection and print any tips (T-1360). Detection runs BEFORE
    recording -- reading `detect_footguns` after `record_cli_event` would
    let this very invocation match as its own "prior" record. Tips never
    change control flow; a detector failure is swallowed, matching
    `append_event`'s own best-effort discipline.

    T-1360 regression fix: the `tree_hash(root)` computed here for
    `detect_footguns` spawns `git` via `frob.gitio.run_argv`, exactly like
    the one inside `record_cli_event` -- but this call site was not wrapped
    in `quiet_stdout_logs()`, so gitio's INFO-level spawn log leaked onto
    stdout ahead of `record_cli_event`'s own quieting, corrupting any
    `--json` command's stdout payload. `quiet_stdout_logs()` is reentrant
    and thread-safe (T-0125), so wrapping it here too is safe even though
    `record_cli_event` wraps its own inner call again."""
    from frob.logging.quiet import quiet_stdout_logs

    tips: list[Tip] = []
    if not tips_disabled():
        try:
            with quiet_stdout_logs():
                tree_hash_value = tree_hash(root)
            tips = detect_footguns(
                root,
                subcommand=subcommand,
                args_head=redact_command(args_head),
                duration_ms=duration_ms,
                exit_code=exit_code,
                tree_hash_value=tree_hash_value,
            )
        except Exception as exc:  # pragma: no cover - defensive, best-effort
            _log.debug("telemetry: footgun detection failed (ignored): %s", exc)
    record_cli_event(
        root,
        subcommand=subcommand,
        args_head=args_head,
        duration_ms=duration_ms,
        exit_code=exit_code,
    )
    # T-1360 delivery requirement: tips must be machine-readable when the
    # invocation itself asked for `--json` -- an agent parsing stdout as
    # JSON cannot also parse a human-styled line appended after it, and
    # a per-subcommand flag name (`doctor_json`, `stats_json`, ...) is
    # not available generically at this call site, so the raw args head
    # is checked directly.
    as_json = "--json" in args_head.split()
    rendered = render_tips(tips, as_json=as_json)
    if rendered:
        _log.warning(rendered)


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:raises Exception
# frob:waive AFFECT001 reason="T-1465 is a pure ARCH001 line-count split (extracted \
# _exit_code_from_system_exit/_finish_timed_call helpers, preserving behavior \
# verbatim, 26 tests in tests/test_telemetry.py still green); the documented public \
# contract is unchanged, so docs/guides/agentic-time-profiling.md#public-api and \
# docs/modules/stats.md need no update"
# frob:tests tests/test_telemetry.py::test_timed_call_records_event_and_returns_value  # noqa: E501
def timed_call(
    root: Path, *, subcommand: str, args_head: str, fn: Callable[[], T]
) -> T:
    """Run `fn()`, recording a `record_cli_event` regardless of outcome
    (including a `SystemExit`, which argparse-style CLI handlers raise for
    non-zero exits) -- the caller's exception/SystemExit still propagates
    unchanged after the event is written.

    T-1360: also runs footgun detection AFTER recording and prints any tips
    to stderr (`_log.warning`, never stdout -- a `--json` command's own
    stdout must stay parseable) before the exception/SystemExit continues
    propagating. Tips never change control flow or the return value; a
    detector failure of its own is swallowed, matching `append_event`'s
    own best-effort discipline."""
    start = time.monotonic()
    exit_code = 0
    try:
        return fn()
    except SystemExit as exc:
        exit_code = _exit_code_from_system_exit(exc)
        raise
    except Exception:
        exit_code = 1
        raise
    finally:
        duration_ms = (time.monotonic() - start) * 1000.0
        _finish_timed_call(
            root,
            subcommand=subcommand,
            args_head=args_head,
            duration_ms=duration_ms,
            exit_code=exit_code,
        )


# T-2694: imported at the BOTTOM, after every event-recording name above is
# defined -- `_footguns`/`_usage` each do `from . import ...` to reach back
# into THIS partially-initialized module for `is_disabled`/`_telemetry_path`,
# so those names must already exist on this module object before either
# submodule import runs (importing them at the top would be a circular-
# import failure: `_footguns`/`_usage` importing from a `frob.app.telemetry`
# that has not finished executing yet).
from ._footguns import (  # noqa: E402
    Tip,
    detect_footguns,
    render_tips,
    tips_disabled,
)
from ._usage import SubcommandTimeSink, UsageReport, usage_report  # noqa: E402

__all__ = [
    "TELEMETRY_REL",
    "SubcommandTimeSink",
    "Tip",
    "UsageReport",
    "append_event",
    "detect_footguns",
    "estimate_tokens",
    "is_disabled",
    "iso_now",
    "record_cli_event",
    "record_ticket_event",
    "redact_command",
    "render_tips",
    "timed_call",
    "tips_disabled",
    "tree_hash",
    "usage_report",
]
