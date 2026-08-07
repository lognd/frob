"""Non-gated agentic time/token telemetry stream (T-0178).

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
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

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
def is_disabled() -> bool:
    """True when the operator opted out via `FROB_NO_TELEMETRY` (any
    non-empty, non-`0`/`false` value)."""
    value = os.environ.get(
        _NO_TELEMETRY_ENV, ""
    )  # frob:waive SEC110 reason="opt-out flag, not a secret"
    return value.strip().lower() not in ("", "0", "false")


# frob:doc docs/guides/agentic-time-profiling.md#public-api
def iso_now() -> str:
    """Current UTC time as an ISO-8601 timestamp with a `Z` suffix -- the
    single timestamp format every telemetry record and ticket-transition
    event in this module uses, so downstream aggregation never has to
    reconcile two shapes."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:invariant INV-022
# invariant spec: [INV-022](invariants/INV-022.md)
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
def estimate_tokens(text: str) -> int:
    """Rough `len(text) / 4` token estimate -- the documented heuristic
    method (T-0178 addendum a); cheap and good enough to rank tools by
    cumulative output size, not intended as an exact tokenizer count."""
    return max(0, len(text) // 4)


# frob:doc docs/guides/agentic-time-profiling.md#public-api
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
        }
        append_event(root, record)


# frob:doc docs/guides/agentic-time-profiling.md#public-api
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
# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::TestRecordDispatchEvent.test_start_and_end_events_shaped_correctly  # noqa: E501
# frob:tests tests/test_telemetry.py::TestRecordDispatchEvent.test_optional_fields_omitted_when_none  # noqa: E501
# frob:waive WIRE001 reason="no caller yet -- the real call site is a Claude Code \
# SessionStart/Stop hook (.claude/hooks/**), deliberately outside T-1724's own scope \
# (schema + join, not the hook wiring)" follow_up="T-1787"
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

    No caller wires this yet (T-1724's own scope is the schema and the
    join, not the Claude Code hook that would call it at session
    start/stop) -- that wiring is a `.claude/hooks/**` change, deliberately
    out of this ticket's declared scope; see its Done report."""
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


# frob:ticket T-1360
_NO_FOOTGUN_TIPS_ENV = "FROB_NO_FOOTGUN_TIPS"
"""Opt-out env var for footgun tips specifically -- distinct from
`FROB_NO_TELEMETRY`, which also stops recording. A caller may want the
corpus recorded but not the post-command nag."""

# frob:ticket T-1360
_SUPPRESS_TIPS_ENV = "FROB_SUPPRESS_TIPS"
"""Comma-separated rule ids (e.g. `FAST_EXIT1,REDUNDANT_RERUN`) individually
suppressed -- a tip that nags gets ignored, which is worse than no tip
(T-1360's own delivery requirement)."""

# frob:ticket T-1360
_FAST_EXIT_MS = 2000.0
"""Duration threshold under which a nonzero exit is flagged as `FAST_EXIT1`
-- short enough that the command plausibly failed before doing real work,
per T-1360's corpus mining (756 such runs)."""

# frob:ticket T-1360
_REDUNDANT_LOOKBACK = 200
"""How many trailing telemetry records `detect_footguns` scans for a prior
identical (subcommand, args_head, tree_hash) or repeated-failure match --
bounded so detection stays O(1)-ish relative to a large corpus rather than
re-reading the whole file every invocation."""

# frob:ticket T-1360
_REPEATED_FAILURE_STREAK = 3
"""Consecutive identical failing invocations (same subcommand + args_head,
each nonzero exit, no successful run of the same command in between)
required before `REPEATED_FAILURE` fires -- one or two retries is normal
iteration, three in a row with no change is stuck."""


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
class Tip(BaseModel):
    """One footgun-detector finding (T-1360): a command that completed but
    looked like a different result than what actually happened (silently
    redundant, silently erroring fast, silently under-verified, silently
    stuck). Printed AFTER the command it concerns, never blocking it;
    `--json`-serializable so an agent -- the primary consumer per the
    ticket -- can parse and self-correct rather than relying on a
    human-styled hint."""

    model_config = {}

    rule_id: str
    message: str
    suggested_command: str | None = None


# frob:ticket T-1360
def _suppressed_rule_ids() -> frozenset[str]:
    """Rule ids named in `FROB_SUPPRESS_TIPS` (comma-separated), normalized
    to upper case -- an empty/unset env yields an empty set, suppressing
    nothing."""
    raw = os.environ.get(_SUPPRESS_TIPS_ENV, "")
    return frozenset(part.strip().upper() for part in raw.split(",") if part.strip())


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
def tips_disabled() -> bool:
    """True when tips are opted out entirely via `FROB_NO_FOOTGUN_TIPS`
    (any non-empty, non-`0`/`false` value) or telemetry itself is disabled
    (`is_disabled()`) -- no corpus, no detection."""
    if is_disabled():
        return True
    value = os.environ.get(
        _NO_FOOTGUN_TIPS_ENV, ""
    )  # frob:waive SEC110 reason="opt-out flag, not a secret"
    return value.strip().lower() not in ("", "0", "false")


# frob:ticket T-1360
def _read_recent_cli_events(root: Path, limit: int) -> list[dict[str, Any]]:
    """Up to `limit` most recent `kind=\"cli\"` records from `root`'s
    telemetry stream, oldest first. Missing/unreadable file yields an empty
    list -- detection is best-effort, same as recording itself."""
    path = _telemetry_path(root)
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        _log.debug("telemetry: read failed (ignored): %s", exc)
        return []
    events: list[dict[str, Any]] = []
    for line in lines[-limit * 4 :]:  # cli + ticket records interleaved; overscan
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("kind") == "cli":
            events.append(record)
    return events[-limit:]


# frob:ticket T-1360
def _tip_redundant_rerun(
    history: list[dict[str, Any]],
    *,
    subcommand: str,
    args_head: str,
    tree_hash_value: str,
) -> Tip | None:
    """`REDUNDANT_RERUN`: an EARLIER `history` record shares this run's
    `(subcommand, args_head, tree_hash)` exactly -- the tree has not
    changed since, so this run's result could not have differed."""
    for prior in reversed(history):
        if (
            prior.get("subcommand") == subcommand
            and prior.get("args_head") == args_head
            and prior.get("tree_hash") == tree_hash_value
        ):
            return Tip(
                rule_id="REDUNDANT_RERUN",
                message=(
                    f"you ran 'frob {args_head}' at this exact "
                    f"tree state (tree_hash={tree_hash_value}) before, at "
                    f"{prior.get('iso_ts', 'an earlier time')}; nothing has "
                    "changed since -- this run could not have produced a "
                    "different result."
                ),
                suggested_command=None,
            )
    return None


# frob:ticket T-1360
def _tip_fast_exit1(
    *, args_head: str, duration_ms: float, exit_code: int
) -> Tip | None:
    """`FAST_EXIT1`: this run itself exited nonzero in under `_FAST_EXIT_MS`
    -- the trap T-1360's own coordinator incident hit (a 0.77s error read
    as a 180x speedup)."""
    if exit_code == 0 or duration_ms >= _FAST_EXIT_MS:
        return None
    return Tip(
        rule_id="FAST_EXIT1",
        message=(
            f"'frob {args_head}' exited with an ERROR "
            f"(exit={exit_code}) in {duration_ms:.0f}ms; it did NOT do the "
            "work you may think it did -- a fast failure is not a fast "
            "success."
        ),
        suggested_command=None,
    )


# frob:ticket T-1360
def _tip_repeated_failure(
    history: list[dict[str, Any]],
    *,
    subcommand: str,
    args_head: str,
    exit_code: int,
) -> Tip | None:
    """`REPEATED_FAILURE`: this run is the Nth (>= `_REPEATED_FAILURE_STREAK`)
    consecutive failure of the identical `(subcommand, args_head)` in
    `history` with no intervening success -- stuck, not progressing."""
    if exit_code == 0:
        return None
    streak = 1
    for prior in reversed(history):
        if prior.get("subcommand") != subcommand or prior.get("args_head") != args_head:
            continue
        if prior.get("exit") == 0:
            break
        streak += 1
        if streak >= _REPEATED_FAILURE_STREAK:
            break
    if streak < _REPEATED_FAILURE_STREAK:
        return None
    return Tip(
        rule_id="REPEATED_FAILURE",
        message=(
            f"'frob {args_head}' has now failed "
            f"{streak} times in a row with no successful run in "
            "between -- this looks stuck, not progressing; "
            "re-running the identical command is unlikely to help."
        ),
        suggested_command=None,
    )


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
def detect_footguns(
    root: Path,
    *,
    subcommand: str,
    args_head: str,
    duration_ms: float,
    exit_code: int,
    tree_hash_value: str,
) -> list[Tip]:
    """Footgun tips for the CLI invocation just completed (T-1360),
    evaluated against the trailing telemetry corpus. Three of the ticket's
    named rules are implemented here, one per `_tip_*` helper (the fourth,
    coverage-number misuse, ties to T-1335 and is out of this ticket's
    scope per its own Description): `REDUNDANT_RERUN`, `FAST_EXIT1`,
    `REPEATED_FAILURE` -- see each helper's own docstring.

    Suppressed rule ids (`FROB_SUPPRESS_TIPS`) are filtered out before
    returning. Returns `[]` when tips are disabled (`tips_disabled()`) --
    callers should check that first to skip the read entirely, but this
    function re-derives nothing unsafe if called anyway."""
    if tips_disabled():
        return []
    suppressed = _suppressed_rule_ids()
    history = _read_recent_cli_events(root, _REDUNDANT_LOOKBACK)

    candidates = (
        _tip_redundant_rerun(
            history,
            subcommand=subcommand,
            args_head=args_head,
            tree_hash_value=tree_hash_value,
        ),
        _tip_fast_exit1(
            args_head=args_head, duration_ms=duration_ms, exit_code=exit_code
        ),
        _tip_repeated_failure(
            history, subcommand=subcommand, args_head=args_head, exit_code=exit_code
        ),
    )
    return [
        tip for tip in candidates if tip is not None and tip.rule_id not in suppressed
    ]


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
def render_tips(tips: list[Tip], *, as_json: bool) -> str:
    """`tips` formatted for post-command display: one `model_dump_json`
    array when `as_json` (the machine-readable form T-1360 requires so an
    agent can self-correct), else one human-readable `[RULE_ID] message`
    line per tip. Returns `\"\"` for an empty list either way -- callers
    should skip printing entirely rather than print an empty JSON array,
    to avoid corrupting a `--json` command's own stdout (same discipline
    as `record_cli_event`'s `quiet_stdout_logs` requirement)."""
    if not tips:
        return ""
    if as_json:
        return json.dumps([t.model_dump() for t in tips])
    return "\n".join(f"[{t.rule_id}] {t.message}" for t in tips)


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
class SubcommandTimeSink(BaseModel):
    """One subcommand's aggregate cost across the whole corpus (T-1360's
    `frob doctor usage` deliverable) -- ranked by `total_duration_ms`
    descending in `UsageReport.top_time_sinks`."""

    model_config = {}

    subcommand: str
    calls: int
    total_duration_ms: float
    failures: int


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
class UsageReport(BaseModel):
    """`frob doctor usage`'s report (T-1360's fourth delivery requirement):
    top time sinks and footgun totals mined from the local telemetry
    corpus -- the same numbers T-1360's own Description mined by hand
    (2.55h wasted on redundant re-runs, 756 fast-exit-1 runs, 11% overall
    failure rate) are now a command, not an ad-hoc script."""

    model_config = {}

    total_calls: int
    total_duration_ms: float
    failures: int
    failure_rate: float
    top_time_sinks: list[SubcommandTimeSink]
    redundant_rerun_count: int
    redundant_rerun_wasted_ms: float
    fast_exit1_count: int
    repeated_failure_streaks: int


# frob:ticket T-1360
def _all_cli_events(root: Path) -> list[dict[str, Any]]:
    """Every `kind=\"cli\"` record in `root`'s telemetry stream, oldest
    first -- `usage_report`'s corpus-wide scan needs the whole history, not
    `_read_recent_cli_events`'s bounded lookback window."""
    path = _telemetry_path(root)
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        _log.debug("telemetry: read failed (ignored): %s", exc)
        return []
    events: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("kind") == "cli":
            events.append(record)
    return events


def _top_time_sinks(
    events: list[dict[str, Any]], *, top_n: int
) -> list[SubcommandTimeSink]:
    """Per-subcommand call count/total duration/failure count from `events`,
    the `top_n` costliest by total duration, descending -- `usage_report`'s
    time-sink ranking."""
    by_subcommand: dict[str, list[float | int]] = {}
    for e in events:
        sub = str(e.get("subcommand", ""))
        bucket = by_subcommand.setdefault(sub, [0, 0.0, 0])
        bucket[0] = int(bucket[0]) + 1
        bucket[1] = float(bucket[1]) + float(e.get("duration_ms", 0.0))
        if e.get("exit") != 0:
            bucket[2] = int(bucket[2]) + 1
    return sorted(
        (
            SubcommandTimeSink(
                subcommand=sub,
                calls=int(calls),
                total_duration_ms=float(dur),
                failures=int(fails),
            )
            for sub, (calls, dur, fails) in by_subcommand.items()
        ),
        key=lambda s: s.total_duration_ms,
        reverse=True,
    )[:top_n]


def _redundant_rerun_totals(events: list[dict[str, Any]]) -> tuple[int, float]:
    """(count, wasted_ms) for `events` whose `(subcommand, args_head,
    tree_hash)` repeats an EARLIER event exactly -- each repeat after the
    first is provably redundant (the tree had not changed)."""
    seen: dict[tuple[str, str, str], bool] = {}
    redundant_count = 0
    redundant_wasted_ms = 0.0
    for e in events:
        key = (
            str(e.get("subcommand", "")),
            str(e.get("args_head", "")),
            str(e.get("tree_hash", "")),
        )
        if key in seen:
            redundant_count += 1
            redundant_wasted_ms += float(e.get("duration_ms", 0.0))
        else:
            seen[key] = True
    return redundant_count, redundant_wasted_ms


def _repeated_failure_streak_count(events: list[dict[str, Any]]) -> int:
    """How many times a run of `_REPEATED_FAILURE_STREAK`-or-more
    consecutive identical `(subcommand, args_head)` failures occurs across
    `events`, with no intervening success resetting the streak."""
    streak_key: tuple[str, str] | None = None
    streak_len = 0
    repeated_failure_streaks = 0
    for e in events:
        key2 = (str(e.get("subcommand", "")), str(e.get("args_head", "")))
        if e.get("exit") != 0 and key2 == streak_key:
            streak_len += 1
            if streak_len == _REPEATED_FAILURE_STREAK:
                repeated_failure_streaks += 1
        elif e.get("exit") != 0:
            streak_key = key2
            streak_len = 1
        else:
            streak_key = None
            streak_len = 0
    return repeated_failure_streaks


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:waive AFFECT001 reason="T-1465 is a pure ARCH001 line-count split (extracted \
# _top_time_sinks/_redundant_rerun_totals/ _repeated_failure_streak_count helpers, \
# preserving behavior verbatim, 26 tests in tests/test_telemetry.py still green); the \
# documented public contract is unchanged, so \
# docs/guides/agentic-time-profiling.md#public-api needs no update"
def usage_report(root: Path, *, top_n: int = 10) -> UsageReport:
    """Aggregate `root`'s whole telemetry corpus into a `UsageReport`
    (T-1360): per-subcommand time sinks, provably-redundant re-run cost
    (identical `(subcommand, args_head, tree_hash)` seen twice), fast-exit
    failures, and stuck-repeat streaks. Read-only, corpus-wide, and cheap
    relative to the run it summarizes -- a single linear pass over the
    file. Empty/missing corpus yields an all-zero report, never an error."""
    events = _all_cli_events(root)
    total_calls = len(events)
    total_duration_ms = sum(float(e.get("duration_ms", 0.0)) for e in events)
    failures = sum(1 for e in events if e.get("exit") != 0)
    failure_rate = (failures / total_calls) if total_calls else 0.0

    top_time_sinks = _top_time_sinks(events, top_n=top_n)
    redundant_count, redundant_wasted_ms = _redundant_rerun_totals(events)
    fast_exit1_count = sum(
        1
        for e in events
        if e.get("exit") != 0 and float(e.get("duration_ms", 0.0)) < _FAST_EXIT_MS
    )
    repeated_failure_streaks = _repeated_failure_streak_count(events)

    return UsageReport(
        total_calls=total_calls,
        total_duration_ms=total_duration_ms,
        failures=failures,
        failure_rate=failure_rate,
        top_time_sinks=top_time_sinks,
        redundant_rerun_count=redundant_count,
        redundant_rerun_wasted_ms=redundant_wasted_ms,
        fast_exit1_count=fast_exit1_count,
        repeated_failure_streaks=repeated_failure_streaks,
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
