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

# frob:ticket T-3695
#: T-3695: `--help`/`-h`/`--version`/`--dry-run` anywhere in the command
#: (word-boundary so `-h` never matches inside a longer flag/word) makes
#: the invocation read-only and fast, regardless of which guarded verb it
#: names -- `uv run frob ticket new --help` cannot stall the way a real
#: `ticket new` can, so it should never need the large-timeout wrapper.
_HELP_OR_DRY_RUN_RE = re.compile(r"(?:^|\s)(?:--help|-h|--version|--dry-run)\b")

# frob:ticket T-3615
#: T-3615: the SAME `frob ticket land` invocation the PATTERN above
#: guards, but explicitly DETACHED per the documented recipe --
#: `setsid`/`nohup` in command position ahead of it, its output
#: redirected to a file (never the terminal), and the whole pipeline
#: backgrounded with a trailing `&`. This shell returns to the caller in
#: milliseconds; it is the fix for the 120s-cap stall, not an instance of
#: it, so it must never need the large-timeout wrapper this guard
#: otherwise demands for `land`. Deliberately narrow (all three elements
#: required) so a NAKED `frob ticket land ... &` -- the real stall
#: pattern this guard exists to catch, T-2282's own opening example --
#: still gets refused: that form has no `setsid`/`nohup` and no output
#: redirect, so it satisfies none of the three sub-patterns below.
_DETACH_PREFIX_RE = re.compile(r"\b(?:setsid|nohup)\b")
# frob:ticket T-3615
_TRAILING_BACKGROUND_RE = re.compile(r"&\s*$")
# frob:ticket T-3615
#: A real filesystem-write redirect (never `2>&1`'s fd-dup alone, but
#: `> file 2>&1` still matches on its leading `>`) -- output going
#: somewhere other than the terminal is part of what makes a detached
#: background job SAFE to leave running unattended.
_OUTPUT_REDIRECT_RE = re.compile(r">>?\s*\S")


def _is_detached_land(scanned: str, verb: str | None) -> bool:
    """True when `scanned` (quote-stripped) is the documented detached-
    land recipe for `frob ticket land` -- `setsid`/`nohup` ahead of the
    invocation, an output redirect, and a trailing `&` -- so the caller
    exempts it from `MIN_TIMEOUT_MS` (T-3615): this shell returns
    immediately, distinct from the naked `&` stall pattern this guard
    still refuses."""
    if verb != "land":
        return False
    return bool(
        _DETACH_PREFIX_RE.search(scanned)
        and _OUTPUT_REDIRECT_RE.search(scanned)
        and _TRAILING_BACKGROUND_RE.search(scanned)
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
def _deny(reason: str) -> None:
    """Emit the PreToolUse deny decision for `reason` (shared by both
    refusal paths; split out of `main` under ARCH001)."""
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def _needs_large_timeout(command: str, timeout_ms: int) -> bool:
    """True when `command` is a frob invocation that must carry the large
    timeout: matches PATTERN on quote-stripped text, is not a --help/
    --dry-run form, is not the detached-land recipe, and the given
    timeout is under MIN_TIMEOUT_MS (split out of `main` under ARCH001)."""
    # Quoted text is prose, not program: this guard blocked a command
    # purely because `uv run frob test` appeared inside a quoted string
    # it was carrying. Same class its own docstring warns about.
    scanned = strip_quoted(command)
    # frob:ticket T-3695
    # T-3695: a `--help`/`-h`/`--version`/`--dry-run` flag makes the
    # invocation read-only and fast -- exempt it even when the command
    # also matches PATTERN (e.g. `uv run frob ticket new --help`).
    # Checked on the SAME quote-stripped text as PATTERN, so a flag that
    # only appears inside quoted prose does not falsely exempt a real
    # invocation.
    if _HELP_OR_DRY_RUN_RE.search(scanned):
        return False
    match = PATTERN.search(scanned)
    # frob:ticket T-3615
    # T-3615: the documented detached-land recipe (`setsid nohup uv run
    # frob ticket land ... > log 2>&1 &`) exits in milliseconds -- it is
    # the FIX for the 120s stall, not an instance of it -- so it is
    # exempt from MIN_TIMEOUT_MS the same way --help is, distinct from a
    # naked `frob ticket land ... &` which still needs the large timeout
    # (see `_is_detached_land`'s docstring for why that form still trips
    # this guard).
    if match and _is_detached_land(scanned, match.group(2)):
        return False
    return bool(match) and timeout_ms < MIN_TIMEOUT_MS


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
        _deny(RUN_IN_BACKGROUND_REASON)
        return

    if _needs_large_timeout(command, timeout_ms):
        _deny(REASON)


if __name__ == "__main__":
    main()
