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
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from frob.logging import get_logger

from ._footguns import Tip, detect_footguns, render_tips, tips_disabled
from ._state import (
    TELEMETRY_REL,
    _external_path_arg_hash,
    _home_config_state_hash,
    _telemetry_path,
    is_disabled,
)
from ._usage import SubcommandTimeSink, UsageReport, usage_report

_log = get_logger(__name__)

# frob:doc docs/guides/agentic-time-profiling.md#public-api
T = TypeVar("T")
"""Generic return type `timed_call` preserves from the wrapped callable."""


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
