---
id: T-3993
title: 'F-209: ledger verbs run for minutes in silence, so the harness backgrounds
  them and agents stall (F-138 recurrence, 3x in one ticket)'
state: queued
kind: ux
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_new.py
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
Consumer logand.app-v2 F-209, 2026-09-06, a recurrence of their F-138 and the
THIRD occurrence inside a single ticket (T-0031):

  "Ledger verbs that write one file take minutes under load; the harness then
   backgrounds them and the agent waits. Profile the verb path (the tickets
   index rebuild? the auto-commit?) and print what it is doing."

THE ASK IS OBSERVABILITY, NOT SPEED, and that is the right ask. Note what they
did NOT request: they did not ask for the verb to be fast. They asked for it to
SAY WHAT IT IS DOING. A slow operation that reports progress is tolerable; a
silent one is indistinguishable from a hang, and that is the actual cost.

CONFIRMED IN THIS REPO THE SAME DAY, AND IT COST AN HOUR. Two `frob ticket new`
calls here were killed at 300s and then at 900s. More expensively, an implementer
agent backgrounded a ledger verb, reported "waiting for the background process to
complete", and ended its turn with finished work sitting unlanded in its
worktree -- twice. That is precisely the failure mode this report names: the
harness backgrounds the verb and the agent waits. The work was complete; only the
land was missing.

A CORRECTION I OWE THIS TICKET, because I got the attribution partly wrong
earlier today. I first recorded "frob ticket new is expensive" as a property of
the verb, then measured the machine (load 41, swap in use, 43 forkservers) and
RETRACTED that, concluding the verb was fine and the box was saturated. This
report shows the retraction went too far. Both are true: load is the amplifier,
AND the baseline cost is already high enough to breach a 120s budget on someone
else's machine, three times in one ticket. Do not let my earlier retraction be
read as "there is nothing here".

WHAT TO DO, IN ORDER:
1. MEASURE FIRST, on an idle machine, with a repo of this size. Get the real
   baseline for `ticket new` and `scope --add` before changing anything. The
   consumer offers two hypotheses -- the tickets index rebuild and the
   auto-commit -- and BOTH ARE HYPOTHESES, not findings. Profile the path and
   report where the time actually goes. This repo's rule is that a consumer's
   symptom is reliable and their mechanism is not.
2. MAKE IT SAY WHAT IT IS DOING. A ledger verb that will run longer than a few
   seconds should emit progress naming the phase (index rebuild, closure
   analysis, auto-commit). This alone resolves the reported friction even if the
   total time does not change, and it is what turns "is it hung?" into a
   question with an answer.
3. ONLY THEN consider making it faster, guided by (1).

NOTE THE SCOPE-CLOSURE ANGLE, worth measuring specifically: filings in this repo
routinely emit dozens of scope-closure warnings (one recent `scope --add` printed
40, another 84). If closure analysis is the dominant cost, that is both the
answer to (1) and a lever -- the analysis is advisory, and paying minutes for
advisory output is a bad trade.

DO NOT fix this by raising timeouts or by telling users to background the verb.
Backgrounding it is exactly what produces the stalled-agent failure above.

MUST-FIRE FIXTURE: a ledger verb exceeding a short threshold emits phase
progress.
MUST-STAY-QUIET: a fast verb stays quiet -- no progress spam on the common case.

ACCEPTANCE
- Measured baseline on an idle machine, with the dominant phase named.
- Progress output for long-running ledger verbs.
- Any speedup justified by the measurement rather than by the consumer's guess.
- Both fixtures committed.