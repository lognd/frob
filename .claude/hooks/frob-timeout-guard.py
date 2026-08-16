"""PreToolUse Bash hook: refuse long-running frob verbs without a large tool timeout.

Long frob commands (ticket land / ticket done-report / ticket work /
ticket new / check / test) that run without an explicit large Bash
TOOL-level timeout get auto-backgrounded at the 120s default cap, and
agents then stall waiting for a notification -- the recurring stall
pattern this drive has nudged 6+ times. A shell-level `timeout N` wrapper
does NOT extend the tool cap, so this guard keys on the tool parameter
itself and tells the caller exactly how to re-run.

T-2248: `ticket work` (creates a worktree, merges main, builds natives)
and `ticket new` (ledger-allocator-lock contention behind in-flight
lands, and NOT safely re-runnable if backgrounded -- a killed/re-run
`ticket new` allocates a second ticket id) both measured exceeding the
120s foreground cap the same way the four originally-guarded verbs do
(T-2248 ticket body: `ticket new` auto-backgrounded mid-filing; `ticket
work T-2239` was backgrounded and stalled an agent). Other frob verbs
(`ticket show`, `ticket list`, `ticket scope`, `verify status`, etc.)
stay unguarded deliberately -- they are fast, and guarding them would
train a reflexive huge timeout that defeats this guard everywhere.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shellscan import strip_quoted  # noqa: E402

# frob:doc docs/guides/claude-hooks.md#frob-timeout-guardpy
MIN_TIMEOUT_MS = 300000
# Command-position only: start-of-line, after a shell connector, or after
# `uv run` (optionally timeout-wrapped) -- so prose mentions of frob verbs
# inside heredocs/echo strings do not false-positive (first FP was a
# coordinator memory-checkpoint heredoc).
# frob:doc docs/guides/claude-hooks.md#frob-timeout-guardpy
PATTERN = re.compile(
    r"(?:^|[;&|(]\s*|\buv +run +)(?:timeout +\d+ +)?"
    r"frob +(ticket +(land|done-report|work|new)|check|test)\b",
    re.M,
)

# frob:doc docs/guides/claude-hooks.md#frob-timeout-guardpy
REASON = (
    "BLOCKED by project hook (frob-timeout-guard): this frob command can "
    "exceed the 120s foreground cap and get auto-backgrounded -- the known "
    "stall pattern. Re-run the SAME command in one Bash call with the "
    "tool-level parameter timeout: 600000 plus a shell-level `timeout 540 "
    "...` wrapper. Never background it, never poll, never end your turn "
    "waiting for it."
)


# frob:doc docs/guides/claude-hooks.md#frob-timeout-guardpy
def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") or ""
    timeout_ms = tool_input.get("timeout") or 0
    # Quoted text is prose, not program: this guard blocked a command
    # purely because `uv run frob test` appeared inside a quoted string
    # it was carrying. Same class its own docstring warns about.
    if PATTERN.search(strip_quoted(command)) and timeout_ms < MIN_TIMEOUT_MS:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": REASON,
                    }
                }
            )
        )


if __name__ == "__main__":
    main()
