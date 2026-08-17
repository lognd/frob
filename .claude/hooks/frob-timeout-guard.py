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

T-2282: enumeration is the whole class of brittleness here -- the very
next stall after T-2248 used a command not on this list at all
(`python3 scripts/fleet_status.py`). This module now ALSO denies an
explicit `run_in_background=true` outright, in agent context
(`FROB_AGENT` set) only, on ANY command -- a check on the structured
parameter the harness already hands this hook, not another name to
enumerate. The stranding case this cannot catch (the harness's own ~120s
auto-background, which no PreToolUse hook can see at all) is closed
separately by the Stop-time `pending-background-guard.py`, which fires on
the actual stranding rather than on how the task was created.
"""

import json
import os
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
RUN_IN_BACKGROUND_REASON = (
    "BLOCKED by project hook (frob-timeout-guard): explicit "
    "run_in_background=true is refused for a dispatched worktree agent "
    "(FROB_AGENT is set) on ANY command, not just an enumerated list -- "
    "T-2248's verb-list guard was bypassed the very next stall by a "
    "non-frob command (`python3 scripts/fleet_status.py`), so this checks "
    "the structured parameter directly instead of extending the list "
    "again. There is no agent-initiated background mode where the "
    "completion notification can reach you (playbook sec 3b) -- run the "
    "SAME command in the FOREGROUND with tool-level timeout: 600000 plus "
    "a shell-level `timeout 540 ...` wrapper instead. (The coordinator's "
    "own shell has no FROB_AGENT set and is unaffected by this rule -- it "
    "may still background a long measurement.)"
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

    # T-2282: an explicit run_in_background=true, in agent context, is
    # refused on the STRUCTURED PARAMETER regardless of which command it
    # names -- keying on command-name enumeration is exactly what let the
    # T-2248 guard get bypassed by the next stall's non-frob command.
    # Scoped to FROB_AGENT (dispatched worktree agents) so the
    # coordinator's own legitimate long-measurement backgrounding is
    # unaffected -- this bans the CONTEXT, not the capability.
    # frob:waive SEC110 reason="FROB_AGENT is a boolean context flag (T-0574), never a \
    # secret"
    if os.environ.get("FROB_AGENT") and tool_input.get("run_in_background") is True:
        # frob:waive RENDER001 reason="standalone Claude Code hook script, no frob \
        # import; stdout IS the hook's JSON-decision contract"
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": RUN_IN_BACKGROUND_REASON,
                    }
                }
            )
        )
        return

    # Quoted text is prose, not program: this guard blocked a command
    # purely because `uv run frob test` appeared inside a quoted string
    # it was carrying. Same class its own docstring warns about.
    if PATTERN.search(strip_quoted(command)) and timeout_ms < MIN_TIMEOUT_MS:
        # frob:waive RENDER001 reason="standalone Claude Code hook script, no frob \
        # import; stdout IS the hook's JSON-decision contract"
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
