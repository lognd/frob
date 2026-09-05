---
id: T-3851
title: 'frob-suggest ack is line-anchored while its trigger scan is not: a per-segment
  FROB_SUGGEST_ACK=1 is ignored'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported as typani FROBLEMS T-016. VERIFIED against the source 2026-09-05.

.claude/hooks/frob-suggest.py:451

    _ACK_PREFIX = re.compile(r"^\s*FROB_SUGGEST_ACK=1\s+")

The acknowledgement is matched with `^` against the WHOLE command string, so it
is honoured only when it is the first token of the entire command line. A
compound command whose flagged segment carries its own ack -- but whose first
token is something else -- is treated as un-acked and blocked.

REPORTER'S MEASURED CASE (6 lost round trips in one session):

    FROB_SUGGEST_ACK=1 uv run ruff check ... ; \
    FROB_SUGGEST_ACK=1 nice uv run pytest ... ; \
    git commit ...

Every linter invocation carries the ack. The hook still blocked. The same
happens for a python3 heredoc that merely CONTAINS "ruff" in a later
semicolon-separated segment -- the pattern that TRIGGERS the block is found
anywhere in the string, while the ack that DISARMS it is only recognised at
position zero. Those two scans must agree on scope and currently do not.

WHY THERE ARE TWO ACK MECHANISMS, so neither is broken by the fix. Line 655
reads the ack from the environment:

    acked = os.environ.get("FROB_SUGGEST_ACK") == "1"

That is the real environment variable. But an inline `VAR=1 cmd` prefix applies
to the spawned command, NOT to the hook, which is a separately-spawned process
that never inherits it -- the same trap the root-write guard documents for
FROB_COORDINATOR. So the regex exists precisely to catch the inline form the
env check cannot see. Keep both; fix only the scope of the regex one.

THIS IS THE STANDING TOKEN-NOT-LEXICAL RULE AGAIN. A regex over raw command
text cannot tell these apart:

    FROB_SUGGEST_ACK=1 ruff check x.py        acked, must pass
    cd d && FROB_SUGGEST_ACK=1 ruff check     acked, must pass  <- fails today
    echo 'FROB_SUGGEST_ACK=1 ruff check'      NOT a real invocation, must not
                                              count as an ack for a later
                                              genuine one
    ruff check x.py                           un-acked, must block

WHAT TO BUILD. Split the command into segments on the shell's own separators
(`;`, `&&`, `||`, newline, and pipeline boundaries), then decide PER SEGMENT:
a segment is acked if that segment's own leading assignments include
FROB_SUGGEST_ACK=1, or if the process environment carries it. Block only when a
segment that matches a trigger pattern is itself un-acked. Use a real shell
lexer (shlex) rather than a smarter regex; quoting cases are exactly where a
refined pattern will fail next, and a quoted string that merely MENTIONS the ack
must not disarm anything.

IF SEGMENT-AWARENESS IS JUDGED TOO MUCH MACHINERY for a hook, the acceptable
alternative is to make the message TRUE: say plainly that the ack must be the
FIRST TOKEN OF THE WHOLE COMMAND LINE. Today line 703 says "prefix it with
`FROB_SUGGEST_ACK=1 ` up front", which reads as "before the thing being run"
and is why the reporter placed it per-segment. A guard whose documented escape
does not work as documented costs more trust than the guard earns. Pick one and
say which; do not leave the message and the behaviour disagreeing.

RELATED, DO NOT FOLD IN: T-3831 (F-026) reports this same hook blocking
`ruff check` while iterating on a single file. Different complaint, same hook.
Check whether the fix here affects it and say so, but keep the tickets separate.

MUST-FIRE FIXTURES (must still block):
  - a bare un-acked trigger command
  - a compound command where the triggering segment is un-acked and an
    UNRELATED segment carries the ack
  - a quoted string mentioning the ack, with a real un-acked trigger elsewhere
MUST-STAY-QUIET FIXTURES (must pass):
  - the ack as the first token of the whole line (today's behaviour, no regress)
  - the ack leading its own segment after a `cd ... &&`
  - the ack on each triggering segment of a multi-segment command
  - the ack present in the real process environment

ACCEPTANCE
- Segment-aware decision, or the message corrected to match reality -- stated
  explicitly which was chosen and why.
- Both fixture sets committed; the must-fire set matters most, since a hook that
  stops blocking looks exactly like a hook that was fixed.
- Edit the SOURCE at .claude/hooks/frob-suggest.py in this repo, never the
  materialized ~/.claude/hooks copy, and note that a sibling agent syncing from
  a stale worktree can silently revert it (T-3408).
