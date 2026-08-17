"""Stop-event hook: refuse to end a turn that is stranding a pending
background Bash task (T-2282).

CANONICAL COPY. This file is git-tracked and is the source of truth; the
`~/.claude/hooks/` copy is written by `sync-claude-config.py` and must never
be hand-edited (it will be overwritten). Edit here, sync outward.

THE FAILURE MODE THIS CLOSES. An agent runs a long command that becomes a
background task -- either it passed `run_in_background: true` itself, or
the harness auto-backgrounded a foreground call at its ~120s cap. The
agent's turn then ends "waiting for the notification". It is never
resumed: the turn is marked complete, the notification (if any) lands only
as inert transcript data, and the ticket stalls until an operator notices
(T-2282 measured three such stalls in one session).

WHY A PreToolUse GUARD CANNOT CLOSE THIS ALONE. `frob-timeout-guard.py`
denies a Bash call by matching the COMMAND STRING against an enumerated
verb list -- and T-2248 proved enumeration is bypassed the moment a
non-frob command (`python3 scripts/fleet_status.py`) becomes the slow one.
Worse, no PreToolUse hook can see the harness's OWN ~120s auto-background
timer at all -- a command the guard approved can still get backgrounded
out from under it. This hook fires on the STRANDING itself (a turn ending
with an unresolved background task), which is the one point common to
both paths, regardless of command name or how the task was created.

FEASIBILITY (T-2282 acceptance 1): the Stop payload's OWN documented
fields (`session_id`, `transcript_path`, `cwd`, `stop_hook_active`) carry
NO dedicated "pending background tasks" field -- confirmed against the
plugin-dev hook-development skill's documented Stop payload shape, which
lists nothing beyond those four plus `reason`. Pending-task state IS
recoverable, but only indirectly, via `transcript_path` (itself a
documented field): every auto-backgrounded or explicitly-backgrounded Bash
call leaves a structured trace in the transcript JSONL --
`toolUseResult.backgroundTaskId` for the auto-background case, and a
`"running in background with ID: <id>"` tool_result string for the
explicit `run_in_background: true` case -- and a genuine completion is
ALSO written back into the transcript later as a synthetic user turn
tagged `origin.kind == "task-notification"` carrying
`<task-id>ID</task-id>...<status>...</status>` (observed directly in this
repo's own transcripts, both shapes). This hook is a real, evidence-based
answer to acceptance 1: NOT a dedicated field, but the transcript already
on hand is enough to reconstruct the same fact this hook needs -- "is
there a background task this turn started that never resolved" -- without
fabricating any new signal.

DETECTION IS LEXICAL, ON PURPOSE. Same owner-decision posture as
`diagnosis-nudge.py`'s module docstring: plain regex over transcript text,
not a second model call. A start marker's task id is treated as PENDING
unless that same id string reappears LATER in the scanned window, in text
that is not itself another start-pattern's description of the SAME
event -- see `_pending_task_id`'s masking step, needed because one real
background-start is described by two different start patterns at once
(the structured `backgroundTaskId` field and the human-readable
acknowledgement text), which would otherwise "resolve" a task against
itself. A poll of the task's output (BashOutput, a `Read` of the output
file) that happens to mention the id also reads as resolved here even if
the polled output shows the job still running -- a known, accepted false
negative; see the module-level "RESIDUAL GAP" note in T-2282's Done
report for the fuller list of what this does not catch.

ONLY THE TRANSCRIPT TAIL IS READ (`_TAIL_BYTES`), not the whole file --
transcripts observed in this repo range past 40MB, and this hook only
ever needs to know about the MOST RECENT background task, not the
session's full history.

RE-ENTRANCY / NO DEADLOCK (T-2282's own "must not deadlock" constraint,
same mechanism `diagnosis-nudge.py` uses for its rate limit). This hook
blocks the Stop event AT MOST ONCE per turn: on `stop_hook_active=True`
(this hook's own block is what caused the harness to re-invoke Stop) it
never blocks again, even if the same task is still pending -- an agent
that reads the block message and still cannot proceed (or still chooses
to end its turn) can always report-and-stop on the second attempt. The
one guaranteed block is the whole fix: it turns "silently stall forever"
into "get told once, in-turn, what to do instead."
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_TAIL_BYTES = 400_000
"""How many trailing bytes of the transcript JSONL to scan. Bounds the
cost of this hook on a multi-hundred-MB transcript while comfortably
covering many turns' worth of recent tool activity -- the only task that
matters here is the MOST RECENT one."""

_AUTO_BACKGROUND_ID = re.compile(r'"backgroundTaskId"\s*:\s*"([A-Za-z0-9_-]+)"')
"""Auto-backgrounded Bash call: `toolUseResult.backgroundTaskId` set by the
harness itself when a foreground call crosses the ~120s cap."""

_EXPLICIT_BACKGROUND_ID = re.compile(
    r"[Cc]ommand running in background with ID:\s*([A-Za-z0-9_-]+)"
)
"""Explicit `run_in_background: true` acknowledgement text, the tool_result
content the harness returns for that call."""

_AUTO_BACKGROUND_ACK = re.compile(r"moved to the background \(ID:\s*([A-Za-z0-9_-]+)\)")
"""Alternate auto-background phrasing observed in tool_result text (the
120s-timeout acknowledgement message itself, distinct from the structured
`toolUseResult.backgroundTaskId` field carrying the same id)."""

_START_PATTERNS = (_AUTO_BACKGROUND_ID, _EXPLICIT_BACKGROUND_ID, _AUTO_BACKGROUND_ACK)

# frob:doc docs/guides/claude-hooks.md#pending-background-guardpy
REASON = (
    "BLOCKED by project hook (pending-background-guard): this turn is ending "
    "with a background Bash task that has not been resolved in the "
    "transcript (no completion notification, no poll of its output seen). "
    "Ending the turn now will strand it -- the notification cannot restart "
    "a finished turn. Either (1) check its status in ONE foreground Bash "
    "call now (BashOutput, or `timeout 30 cat <output-file>`) and continue "
    "acting on the result, or (2) if you genuinely cannot proceed, say so "
    "explicitly and end your turn as a deliberate report-and-stop -- this "
    "hook will not block a second time."
)


def _tail_text(transcript_path: str) -> str:
    """The last `_TAIL_BYTES` of `transcript_path`, decoded leniently, or
    `""` for any missing/unreadable file -- this hook must fail open, never
    raise, on a transcript it cannot read."""
    try:
        path = Path(transcript_path)
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > _TAIL_BYTES:
                fh.seek(size - _TAIL_BYTES)
            data = fh.read()
        return data.decode("utf-8", errors="replace")
    except OSError:
        return ""


def _pending_task_id(tail: str) -> str | None:
    """The id of a background task that STARTED somewhere in `tail` and is
    never genuinely resolved afterward -- `None` if no start marker is
    present, or every start marker's id is resolved (a completion
    notification or an explicit poll, either one counts; see the module
    docstring's accepted false-negative note). Returns the LAST (most
    recent) unresolved id, since only the most recent task is relevant to
    "is this turn ending with a live strand"."""
    spans: list[tuple[int, int, str]] = []
    for pattern in _START_PATTERNS:
        for match in pattern.finditer(tail):
            spans.append((match.start(), match.end(), match.group(1)))
    if not spans:
        return None
    spans.sort(key=lambda triple: triple[0])

    # A single real background-start event is described by MULTIPLE start
    # patterns at once (the structured `backgroundTaskId` field AND the
    # human-readable acknowledgement text both carry the same id for one
    # event) -- without masking those spans out, the second pattern's
    # mention of the SAME event would read as "the id reappeared later",
    # falsely marking a still-pending task as resolved. Blank every
    # start-pattern span (length preserved as spaces) before searching
    # "after" text, so only a GENUINE later mention -- a completion
    # notification's `<task-id>`, or an id embedded in an unrelated later
    # tool call -- counts as resolution.
    masked = list(tail)
    for start, end, _ in spans:
        for i in range(start, end):
            masked[i] = " "
    masked_tail = "".join(masked)

    pending: str | None = None
    for _, end, task_id in spans:
        if task_id in masked_tail[end:]:
            continue
        pending = task_id
    return pending


def _decision(payload: dict) -> dict | None:
    """The hook's full decision for `payload`, pure apart from the one
    transcript read -- `None` for "let the stop proceed", or the
    `{"decision": "block", ...}` object to print. Split out of `main` so
    the logic is unit-testable without a subprocess."""
    if payload.get("stop_hook_active"):
        return None
    transcript_path = payload.get("transcript_path")
    if not isinstance(transcript_path, str) or not transcript_path:
        return None
    tail = _tail_text(transcript_path)
    if not tail:
        return None
    pending_id = _pending_task_id(tail)
    if pending_id is None:
        return None
    return {
        "decision": "block",
        "reason": REASON,
        "systemMessage": REASON,
    }


# frob:doc docs/guides/claude-hooks.md#pending-background-guardpy
# frob:tests tests/test_hook_pending_background_guard.py kind="integration"
def main() -> int:
    """Entry point: JSON payload on stdin, a `decision: block` object on
    stdout when a pending background task is detected, nothing otherwise.
    Any parse/read failure degrades to silence (exit 0) -- this hook must
    never be the reason a turn cannot end at all."""
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (OSError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0
    decision = _decision(payload)
    if decision is not None:
        # frob:waive RENDER001 reason="standalone Claude Code hook script, no frob \
        # import; stdout IS the hook's JSON-decision contract"
        print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
