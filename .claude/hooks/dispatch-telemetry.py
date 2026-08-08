"""SessionStart/Stop hooks: record a dispatch's start/end boundary (T-1787).

CANONICAL COPY. This file is git-tracked and is the source of truth; the
`~/.claude/hooks/` copy is written by `sync-claude-config.py` and must never
be hand-edited (it will be overwritten). Edit here, sync outward.

WHY THIS EXISTS. T-1724 built `frob.app.telemetry.record_dispatch_event`
(the `kind="dispatch"` boundary record) and `frob.stats.dispatch_cost_report`
(the join against `kind="tool"`/`kind="ticket"` events) but deliberately left
both unwired -- no caller existed anywhere in the repo. This script is that
caller: registered as a `SessionStart` hook it records `event="start"`
(worktree, branch, and `cold_start` -- `True` only when Claude Code's own
payload names this a fresh `"startup"`, `False` for `"resume"`/`"clear"`/
`"compact"`), and registered as a `Stop` hook it records `event="end"`. Both
share one `dispatch_id`: the session's own `session_id`, which Claude Code
keeps stable across every Stop event in a session and issues fresh per
dispatch -- exactly the identity `dispatch_cost_report` needs to join a
dispatch's start mark against its end mark.

NO `frob` IMPORT, DELIBERATELY (matching `diagnosis-nudge.py`'s and
`frob-suggest.py`'s own precedent, not a new decision). Claude Code invokes
this hook with the SYSTEM `python3` (measured 3.10 in this environment),
not the project's `uv`-managed interpreter (3.11+) `frob` itself requires
-- `import frob` here would raise on the very first line (`tomllib`, a
3.11+ stdlib module) and the whole boundary event would silently never be
recorded. This script writes the exact same `kind="dispatch"` JSON-line
shape `record_dispatch_event` writes, directly, with the plain stdlib.

NEVER BLOCKS AND NEVER PRINTS ANYTHING ON A NORMAL RUN. Every write is
best-effort (any `OSError` is swallowed, matching
`frob.app.telemetry.append_event`'s own posture) and this script never
emits a `systemMessage` -- unlike `diagnosis-nudge.py`, there is nothing
here worth surfacing to the operator; recording a boundary event has no
user-visible decision attached to it. A missing repo root or malformed
payload is caught and the script exits 0 silently.

DISPATCH_ID CHOICE. `session_id` is what Claude Code hands every hook
invocation for the current session; using it directly (not a freshly
generated uuid) is what lets a `SessionStart` mark and its matching `Stop`
mark(s) join on the same key without any extra state file.

COLD_START INFERENCE. `SessionStart`'s payload carries a `source` field
(`"startup"`, `"resume"`, `"clear"`, or `"compact"` per Claude Code's own
hook contract) -- `cold_start=True` only for `"startup"`; every other source
resumes prior context and is not a cold start. An unrecognized/missing
`source` records `cold_start=None` (unmeasured, field omitted -- matching
`record_dispatch_event`'s own "omit rather than guess" contract), never
guessed.

TELEMETRY OPT-OUT. Respects `FROB_NO_TELEMETRY` (any non-empty, non-`0`/
`false` value), same env var and same truthiness rule as
`frob.app.telemetry.is_disabled` -- a repo that opted out of telemetry via
one mechanism must not have this hook silently write anyway through a
second, un-opted-out path.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _telemetry_disabled() -> bool:
    """Mirrors `frob.app.telemetry.is_disabled` exactly (same env var, same
    truthiness rule) without importing `frob` -- see the module docstring's
    "NO `frob` IMPORT" note for why this cannot just call that function."""
    value = os.environ.get(
        "FROB_NO_TELEMETRY", ""
    )  # frob:waive SEC110 reason="opt-out flag, not a secret"
    return value.strip().lower() not in ("", "0", "false")


def _iso_now() -> str:
    """Mirrors `frob.app.telemetry.iso_now`'s exact format (UTC, millisecond
    precision, `Z` suffix) so a hook-written record is byte-for-byte
    indistinguishable in shape from one `record_dispatch_event` writes."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _repo_root(cwd: str) -> Path | None:
    """Nearest ancestor of `cwd` containing `.git`, or `None` if this
    session is not inside a git repo -- there is no telemetry stream to
    write to outside one (mirrors `diagnosis-nudge.py`'s own helper)."""
    here = Path(cwd).resolve() if cwd else Path.cwd()
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _run_git(args: list[str], root: Path) -> subprocess.CompletedProcess | None:
    """Spawn `git <args>` in `root`, or `None` on any spawn failure (git
    unavailable, timeout) -- the sole I/O boundary `_current_branch` reads,
    split out so the exit-code/output interpretation below carries no I/O
    of its own."""
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _current_branch(root: Path) -> str | None:
    """`root`'s current git branch name, or `None` on any failure (detached
    HEAD, git unavailable, spawn error, timeout) -- never raises."""
    result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    if result is None or result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _cold_start_from_source(source: object) -> bool | None:
    """`True` only for Claude Code's `"startup"` `SessionStart` source,
    `False` for a recognized resume-shaped source, `None` (unmeasured) for
    anything else -- never guessed."""
    if source == "startup":
        return True
    if source in ("resume", "clear", "compact"):
        return False
    return None


def _append_dispatch_event(root: Path, record: dict) -> None:
    """Append one `kind="dispatch"` JSON line to `root/.frob/telemetry.jsonl`
    -- the same append shape `frob.app.telemetry.append_event` uses
    (`sort_keys=True`, one record per line), reimplemented locally per the
    module docstring's "NO `frob` IMPORT" constraint. Best-effort: any I/O
    failure is swallowed, never raised."""
    if _telemetry_disabled():
        return
    path = root / ".frob" / "telemetry.jsonl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True))
            fh.write("\n")
    except OSError:
        pass


def _handle_session_start(payload: dict) -> None:
    """Record `event="start"` for this dispatch, best-effort."""
    root = _repo_root(str(payload.get("cwd", "")))
    if root is None:
        return
    session_id = str(payload.get("session_id", "unknown"))
    record: dict = {
        "iso_ts": _iso_now(),
        "kind": "dispatch",
        "dispatch_id": session_id,
        "event": "start",
        "worktree": str(root),
    }
    branch = _current_branch(root)
    if branch is not None:
        record["branch"] = branch
    cold_start = _cold_start_from_source(payload.get("source"))
    if cold_start is not None:
        record["cold_start"] = cold_start
    _append_dispatch_event(root, record)


def _handle_stop(payload: dict) -> None:
    """Record `event="end"` for this dispatch, best-effort. Skips the
    re-entrant Stop invocation the harness issues after another Stop hook's
    own `systemMessage` (`stop_hook_active`) -- an `end` mark only needs to
    be recorded once per real stop, and a duplicate is harmless but noisy."""
    if payload.get("stop_hook_active"):
        return
    root = _repo_root(str(payload.get("cwd", "")))
    if root is None:
        return
    session_id = str(payload.get("session_id", "unknown"))
    record = {
        "iso_ts": _iso_now(),
        "kind": "dispatch",
        "dispatch_id": session_id,
        "event": "end",
    }
    _append_dispatch_event(root, record)


def _parse_stdin_payload(raw: str) -> dict | None:
    """`raw`'s stdin text parsed as a JSON object, or `None` for anything
    else -- matches `diagnosis-nudge.py`'s own parser."""
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def main() -> int:
    """Entry point: dispatches on `hook_event_name` in the stdin JSON
    payload (`SessionStart` or `Stop`); unrecognized/missing event names are
    a silent no-op. Always exits 0 -- a telemetry hook must never fail a
    session start or a turn's stop."""
    payload = _parse_stdin_payload(sys.stdin.read())
    if payload is None:
        return 0
    event_name = payload.get("hook_event_name")
    if event_name == "SessionStart":
        _handle_session_start(payload)
    elif event_name == "Stop":
        _handle_stop(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
