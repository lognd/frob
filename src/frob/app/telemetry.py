"""Non-gated agentic time/token telemetry stream (T-0178).

Diagnostics ONLY: no rule ids here, nothing in this module fails a gate or
is consulted by `frob check`. Every `frob` CLI invocation and every ticket
state transition appends one JSON line to `.frob/telemetry.jsonl`, local
only (`.frob/` is gitignored, never networked). Set `FROB_NO_TELEMETRY=1`
to opt out entirely -- `is_disabled()` is the single source of truth every
call site in this module checks before writing anything.

Redaction discipline: any free-text field that might carry a copy-pasted
secret (a command's argv head, a tool-call snippet) is passed through
`redact_command`, which reuses `frob.gates._secrets`'s existing provider
patterns (T-0157) rather than re-deriving a second scanner -- two secret
scanners is exactly the kind of drift-prone duplication the engineering
principles forbid.
"""

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
    """
    from frob.gates._secrets import _redact, _scan_line

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


# frob:doc docs/guides/agentic-time-profiling.md#public-api
def timed_call(
    root: Path, *, subcommand: str, args_head: str, fn: Callable[[], T]
) -> T:
    """Run `fn()`, recording a `record_cli_event` regardless of outcome
    (including a `SystemExit`, which argparse-style CLI handlers raise for
    non-zero exits) -- the caller's exception/SystemExit still propagates
    unchanged after the event is written."""
    start = time.monotonic()
    exit_code = 0
    try:
        return fn()
    except SystemExit as exc:
        # `sys.exit()`/`sys.exit(None)` is conventionally SUCCESS (exit 0);
        # an int code is used as-is; anything else (e.g. a message string)
        # is a non-zero exit per Python's own SystemExit convention.
        if exc.code is None:
            exit_code = 0
        elif isinstance(exc.code, int):
            exit_code = exc.code
        else:
            exit_code = 1
        raise
    except Exception:
        exit_code = 1
        raise
    finally:
        duration_ms = (time.monotonic() - start) * 1000.0
        record_cli_event(
            root,
            subcommand=subcommand,
            args_head=args_head,
            duration_ms=duration_ms,
            exit_code=exit_code,
        )


__all__ = [
    "TELEMETRY_REL",
    "append_event",
    "estimate_tokens",
    "is_disabled",
    "iso_now",
    "record_cli_event",
    "record_ticket_event",
    "redact_command",
    "timed_call",
    "tree_hash",
]
