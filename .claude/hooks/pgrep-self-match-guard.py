#!/usr/bin/env python3
"""PreToolUse Bash hook: deny a command that greps the process table for
a literal pattern that the command itself contains -- `pgrep -f "frob
check"` run from a Bash tool call always finds the `bash -c` shell that
is running it, so a poll loop built on it never exits.

CANONICAL COPY. This file is git-tracked and is the source of truth; the
`~/.claude/hooks/` copy is written by `sync-claude-config.py` and must
never be hand-edited (it will be overwritten). Edit here, sync outward.

THE FAILURE MODE THIS CLOSES. Measured 2026-09-23: 26 of ~40 live harness
shells were pollers that could never exit, 18 of them of the shape
`until ! pgrep -f "frob ticket work T-5364" >/dev/null; do sleep 10;
done`. The Claude Code harness runs every Bash call as `bash -c '<the
command text>'`, so the pattern is a substring of the poller's own
command line and `pgrep -f` matches the poller itself, forever. The
agents' turns then ended "waiting" on a notification that never came,
and the shells outlived the watched command by up to 21 hours.

WHAT IS DENIED. Any `pgrep -f <literal>` whose pattern is a literal
(quoted or bare; a pattern built from a shell variable is not visible to
pgrep as text and passes), and any `ps ... | grep <literal>` that does
not use the `[f]oo` bracket trick. Loop or no loop: a one-shot `pgrep -f`
gives the same wrong answer ("still running") the loop does.

THE RECIPES THAT DO NOT SELF-MATCH, named in the refusal: `pgrep -x
<exe>`; a pattern assembled from a variable (`P="frob che"; P="${P}ck";
pgrep -f "$P"`); the bracket trick (`grep "[f]rob check"`); or, best,
no process-table poll at all -- wait for the harness task notification
of the backgrounded command, or on a pid captured with `$!`.

ONE OVERRIDE (systematize-friction rule): `FROB_SELF_MATCH_ACK=1` in the
environment or as a prefix of the command lets the call through.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shellscan import quoted_spans  # noqa: E402

#: `pgrep` with `-f` (alone or folded into a flag cluster such as `-fl`)
#: followed by a literal pattern: a quoted string with no `$` inside, or
#: a bare word that does not start with `$`.
# frob:doc docs/guides/claude-hooks.md#pgrep-self-match-guardpy
PGREP_LITERAL = re.compile(
    r"\bpgrep\b(?:\s+-[A-Za-z]*)*?\s+-[A-Za-z]*f[A-Za-z]*"
    r"(?:\s+-[A-Za-z]+(?:\s+\S+)?)*"
    r'\s+(?:"([^"$]*)"|\'([^\'$]*)\'|([^\s"\'$|;&)-][^\s"\'$|;&)]*))'
)

#: `ps ... | grep <literal>` where the literal does not open with the
#: `[x]` bracket trick. `grep -v grep` downstream is not honoured on
#: purpose: it drops the grep, not the `bash -c` shell carrying the text.
# frob:doc docs/guides/claude-hooks.md#pgrep-self-match-guardpy
PS_GREP_LITERAL = re.compile(
    r"\bps\b[^|;\n]*\|\s*grep\b(?:\s+-[A-Za-z]+)*"
    r'\s+(?:"([^"$\[][^"$]*)"|\'([^\'$\[][^\']*)\'|([^\s"\'$\[|;&)-][^\s"\'$|;&)]*))'
)

# frob:doc docs/guides/claude-hooks.md#pgrep-self-match-guardpy
ACK_ENV = "FROB_SELF_MATCH_ACK"

# frob:doc docs/guides/claude-hooks.md#pgrep-self-match-guardpy
REASON = (
    "Self-matching process poll: `pgrep -f <literal>` (or `ps | grep "
    "<literal>`) run from a Bash tool call always matches the `bash -c` "
    "shell running this very command, so the check answers 'still "
    "running' forever and a poll loop built on it never exits (26 such "
    "shells measured live on 2026-09-23). Use `pgrep -x <exe>`, assemble "
    'the pattern from a variable (P="frob che"; P="${P}ck"; pgrep -f '
    '"$P"), use the bracket trick (grep "[f]rob check"), or better, do '
    "not poll the process table at all: wait for the harness task "
    "notification of the backgrounded command, or on a pid captured "
    "with $!. Override once you are sure: prefix the command with "
    f"`{ACK_ENV}=1 `."
)


# frob:doc docs/guides/claude-hooks.md#pgrep-self-match-guardpy
# frob:tests tests/test_hook_pgrep_self_match_guard.py kind="integration"
def self_match(command: str) -> str | None:
    """The literal pattern that would self-match, or None when the
    command is safe. A match that STARTS inside a quoted span or heredoc
    body is text the command carries (a commit message, an echo, a `git
    grep` for the word), not a process poll, and is ignored; the poll's
    own quoted argument begins after the match start, so it stays
    visible. Pure so the test suite can drive it directly."""
    spans = quoted_spans(command)
    for pattern in (PGREP_LITERAL, PS_GREP_LITERAL):
        for match in pattern.finditer(command):
            if any(start <= match.start() < end for start, end in spans):
                continue
            literal = next(g for g in match.groups() if g is not None)
            if literal.strip():
                return literal
    return None


# frob:doc docs/guides/claude-hooks.md#pgrep-self-match-guardpy
# frob:tests tests/test_hook_pgrep_self_match_guard.py kind="integration"
def main() -> int:
    """Read the PreToolUse payload from stdin; emit a deny decision when
    the Bash command contains a self-matching process poll."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    command = payload.get("tool_input", {}).get("command", "")
    if not isinstance(command, str):
        return 0
    if os.environ.get(ACK_ENV) == "1" or command.lstrip().startswith(
        f"{ACK_ENV}=1"
    ):
        return 0
    literal = self_match(command)
    if literal is None:
        return 0
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"[pgrep-self-match-guard] pattern {literal!r}: "
                        + REASON
                    ),
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
