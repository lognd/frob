---
id: T-3071
title: frob-suggest ignores FROB_SUGGEST_ACK=1 on the first block of a new command
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/frob-suggest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: Record the measured first-block/ack defect and its acceptance criteria at
    filing time
  actor: logan
  at: '2026-08-26'
  old_length: 0
  new_length: 2415
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-26. `FROB_SUGGEST_ACK=1 ruff check src/ tests/` was BLOCKED
with the "BLOCKED ONCE ... this looks like work frob should account for"
message, despite the acknowledgement being present in the environment. The
identical command run a second time was allowed.

So the ack is consulted only on the REPEAT path, not on the first-block path.
The repeat-block message itself advertises the opposite:

    "prefix it with `FROB_SUGGEST_ACK=1 ` ... that acknowledgement is checked
     every time, so later repeats need it again too, not just once."

"checked every time" is false for the first encounter of a given command
string.

WHY THIS MATTERS RATHER THAN BEING COSMETIC: the ack exists so a caller who
has decided the raw command is right can proceed. As implemented, a caller who
KNOWS in advance that they want the raw command still eats a block, and the
only way through is to re-run the exact same string -- which teaches the habit
of blind re-running rather than reading the nudge. That is the opposite of what
a nudge hook is for, and it is how the message came to be wrong about its own
behaviour.

Related: three of this hook's rules were found MISFIRING on 2026-08-26
(T-2908) and had to be narrowed. This is a fourth defect in the same hook,
which suggests the hook has no fixture coverage for its own control flow, not
just for its patterns.

FIX: consult FROB_SUGGEST_ACK on every path, first block included. If there is
a deliberate reason the first block should ignore the ack -- e.g. wanting the
caller to at least SEE the nudge once -- then say so in the first-block message
instead of leaving it silent, and correct the repeat message's "checked every
time" claim.

ACCEPTANCE
- `FROB_SUGGEST_ACK=1 <command>` passes on the FIRST encounter of that command
  string. Must-stay-quiet fixture.
- The same command WITHOUT the ack is still blocked on first encounter.
  Must-fire fixture -- do not solve this by weakening the hook.
- The block messages describe the implemented behaviour exactly; if the
  first-block path deliberately ignores the ack, both messages say so.
- Fixtures cover the hook's CONTROL FLOW (first block / repeat block / ack /
  no-ack), not only its regex rules -- this is the gap that let the defect sit.
- Hooks are MATERIALIZED from `.claude/hooks/` into `~/.claude/`: edit the
  source, run the sync, and confirm `frob claude sync --check` reports no drift.
