"""Stop-event hook: nudge when a turn diagnoses a defect but files nothing
(T-1734).

CANONICAL COPY. This file is git-tracked and is the source of truth; the
`~/.claude/hooks/` copy is written by `sync-claude-config.py` and must never
be hand-edited (it will be overwritten). Edit here, sync outward.

WHY THIS EXISTS. A coordinator repeatedly diagnoses a defect in prose --
"this is the same class as X", "that is a real bug", "the cost structure
rewards weak evidence" -- and does not file it. Prose is where findings go
to die: the gap is not knowledge, it is that nothing converts a stated
finding into a tracked obligation.

OWNER DECISION 2026-08-07 (binding, recorded on T-1734's acceptance
criteria): lexical matching is fine; an LLM-evaluated hook is REJECTED --
do not pipe the turn's own text through a second model. This hook is a
plain command hook over text (regex, word-boundary-anchored diagnostic
phrasing, never bare substrings like "bug"/"broken" which fire on every
code review) and repo state (did this turn actually run
`frob ticket new`, read from `.frob/telemetry.jsonl`).

NEVER BLOCKS. Emits `{"systemMessage": "..."}` and exits 0, always --
a Stop hook that blocks turns a missing ticket into a stuck session, which
is strictly worse than a missed nudge.

RE-ENTRANCY. The Stop payload carries `stop_hook_active`: `True` when this
Stop hook's own `systemMessage` is what triggered the CURRENT Stop event
(the harness re-invokes Stop hooks once after a non-empty `systemMessage`).
Exiting immediately on `stop_hook_active` is the whole guard -- without it,
a nudge would nudge about its own nudge.

RATE LIMIT. Per `session_id`, at most one nudge per `_MIN_RENUDGE_S`
seconds (state file, see `_STATE_REL`) -- a long turn must not nag
repeatedly, and a nag that fires constantly gets ignored, which is worse
than no nag.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

_MIN_RENUDGE_S = 600.0
"""Minimum seconds between two nudges for the SAME session_id -- a long
turn (many tool calls, one Stop event) must not re-trigger repeatedly."""

_TICKET_FILE_WINDOW_S = 1800.0
"""How far back into `.frob/telemetry.jsonl` to look for a `ticket new`
CLI event before concluding "nothing was filed" -- generous enough to
cover one turn's own work without also covering the PREVIOUS turn's."""

_STATE_REL = Path("hooks") / "state" / "diagnosis-nudge-state.json"
"""Relative to `~/.claude/` -- the rate-limit state file, one entry per
`session_id`. Deliberately NOT under a repo's `.frob/` (a Stop hook is not
scoped to one repo/worktree; a session can move between them)."""

# frob:ticket T-1734
# Word-boundary-anchored diagnostic-CLAIM phrasing, not bare substrings.
# "bug"/"broken"/"should fix" alone fire on every code review, every Done
# report, and every message quoting a ticket title (measured, T-1734's own
# body: three lexical false-positive incidents in one day already). Each
# pattern below requires an assertion SHAPE -- "X is a bug", "root cause
# is Y", "found a defect" -- not just the word appearing anywhere.
_DIAGNOSIS_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bthis is (?:a|the) (?:real|genuine|known)? ?(?:bug|defect|regression)\b",
        r"\b(?:root|actual|real|underlying) cause (?:is|was|:)\s*\S",
        r"\bfound (?:a|another) (?:bug|defect|regression|real issue)\b",
        r"\bthe (?:bug|defect|issue) (?:is|was) (?:that|caused by)\b",
        r"\bthis (?:class|shape) of (?:bug|defect|issue)\b",
        r"\b(?:should|needs? to) (?:be )?file(?:d)? a ticket\b",
        r"\bnot (?:currently )?tracked (?:by|in) (?:a|any) ticket\b",
    )
)


# frob:waive PII012 reason="T-1734: a software-defect finding, not a medical term"
def _detect_diagnosis(text: str) -> str | None:
    """The first ~120-char excerpt around a matched finding-shaped
    sentence in `text`, or `None` if no pattern matched. An excerpt (not
    just "a finding was made") is what lets the nudge message NAME what
    to file rather than merely flag that something is unfiled (T-1734
    acceptance criterion 2)."""
    for pattern in _DIAGNOSIS_PATTERNS:
        match = pattern.search(text)
        if match is None:
            continue
        start = max(0, match.start() - 40)
        end = min(len(text), match.end() + 40)
        excerpt = text[start:end].strip().replace("\n", " ")
        return excerpt
    return None


def _repo_root(cwd: str) -> Path | None:
    """Nearest ancestor of `cwd` containing `.git`, or `None` -- a Stop
    event outside any repo has no telemetry stream to check, so the
    state-based half of the signal cannot run (fails closed: no nudge,
    never a false one)."""
    here = Path(cwd).resolve() if cwd else Path.cwd()
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _recently_filed_ticket(root: Path, *, now_s: float, window_s: float) -> bool:
    """`True` if `root`'s telemetry stream records a `kind="cli"`
    `frob ticket new` invocation within the last `window_s` seconds --
    the state-based half of the conjunction (T-1734's own design: "work
    happened, nothing was filed" is answerable exactly from telemetry,
    with no parsing of prose). Malformed lines are skipped, never raised,
    matching `frob.stats._agentic._load_events`'s posture -- this script
    must not be a NEW way for a corrupt telemetry file to break a Stop
    event."""
    from datetime import datetime

    path = root / ".frob" / "telemetry.jsonl"
    if not path.exists():
        return False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict) or record.get("kind") != "cli":
            continue
        subcommand = str(record.get("subcommand", ""))
        args_head = str(record.get("args_head", ""))
        if subcommand != "ticket" or not args_head.startswith("new"):
            continue
        iso_ts = record.get("iso_ts")
        if not isinstance(iso_ts, str):
            continue
        try:
            ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00")).timestamp()
        except ValueError:
            continue
        if now_s - ts <= window_s:
            return True
    return False


def _load_state(state_path: Path) -> dict[str, float]:
    """`{session_id: last_nudge_epoch_s}`, or `{}` on any parse/read
    failure -- a corrupt rate-limit state file must degrade to
    "not rate-limited" (worst case: one extra nudge), never crash the
    hook."""
    if not state_path.exists():
        return {}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): float(v) for k, v in data.items() if isinstance(v, (int, float))}


def _save_state(state_path: Path, state: dict[str, float]) -> None:
    """Best-effort write, never raised -- state is an optimization
    (fewer duplicate nudges), not a correctness requirement."""
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass


def _should_nudge(
    payload: dict,
    *,
    home: Path,
    now_s: float,
) -> str | None:
    """The full decision, pure apart from the two I/O reads it takes as
    injected paths (`home`) -- returns the `systemMessage` text to emit,
    or `None` for "stay silent". Split from `main` so every branch is
    unit-testable without spawning the script as a subprocess."""
    if payload.get("stop_hook_active"):
        return None
    last_message = payload.get("last_assistant_message")
    if not isinstance(last_message, str) or not last_message.strip():
        return None
    excerpt = _detect_diagnosis(last_message)
    if excerpt is None:
        return None

    session_id = str(payload.get("session_id", "unknown"))
    state_path = home / _STATE_REL
    state = _load_state(state_path)
    last_nudge = state.get(session_id)
    if last_nudge is not None and now_s - last_nudge < _MIN_RENUDGE_S:
        return None

    root = _repo_root(str(payload.get("cwd", "")))
    if root is not None and _recently_filed_ticket(
        root, now_s=now_s, window_s=_TICKET_FILE_WINDOW_S
    ):
        return None

    state[session_id] = now_s
    _save_state(state_path, state)
    return (
        f"This turn stated a diagnosis but filed no ticket: \"...{excerpt}...\". "
        f"If this is a real, actionable finding, run `frob ticket new` for it "
        f"(or `frob ticket new --title ... --kind bug/feature --scope ...`)."
    )


def _parse_stdin_payload(raw: str) -> dict | None:
    """`raw`'s stdin text parsed as a JSON object, or `None` for anything
    else (empty input, malformed JSON, or valid JSON that is not an
    object) -- split out of `main` (ARCH103: keep the parse decision apart
    from the I/O and the nudge decision)."""
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _emit_nudge_if_any(payload: dict) -> None:
    """`_should_nudge`'s decision, plus the one place this script writes
    to stdout -- split out of `main` (ARCH103: keep the print apart from
    the top-level parse/dispatch decision)."""
    home = Path(os.environ.get("HOME", str(Path.home()))) / ".claude"
    message = _should_nudge(payload, home=home, now_s=time.time())
    if message is not None:
        print(json.dumps({"systemMessage": message}))


# frob:doc docs/guides/claude-hooks.md#diagnosis-nudgepy
def main() -> int:
    """Entry point: JSON payload on stdin, `{"systemMessage": ...}` on
    stdout when a nudge fires, nothing otherwise. Always exits 0 -- a
    Stop hook that can fail the turn is worse than one that misses a
    nudge."""
    payload = _parse_stdin_payload(sys.stdin.read())
    if payload is not None:
        _emit_nudge_if_any(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
