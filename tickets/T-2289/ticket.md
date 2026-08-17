---
id: T-2289
title: 'T-1914 sibling-state-regression guard names the LANDING ticket as its own
  sibling: 6 of 6 refusals were self-conflicts, 40% of all land attempts'
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given a land whose only divergent ledger row is the landing ticket's own,
    when frob ticket land runs, then it resolves by keeping the newer state and does
    not refuse
  evidence: []
- text: given a land where a genuine sibling ticket's row would regress, when frob
    ticket land runs, then it still refuses (guard not weakened)
  evidence: []
- text: given the regression tests, when they run, then both the self-conflict and
    genuine-sibling cases are covered as distinct must-pass/must-fail fixtures
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-17 by aggregating all 5 concurrent implementer agents'
Bash transcripts (288 tool calls, 6440s of command wall time).

T-1914's sibling-state-regression guard refused 6 land invocations. In
ALL 6, the "sibling" it named was the ticket being landed itself:

  landing T-2276 -> "regress sibling ticket(s) T-2276"
  landing T-2276 -> "regress sibling ticket(s) T-2276"
  landing T-2269 -> "regress sibling ticket(s) T-2269"
  landing T-2116 -> "regress sibling ticket(s) T-2116"
  landing T-2116 -> "regress sibling ticket(s) T-2116"
  landing T-2112 -> "regress sibling ticket(s) T-2112"

6 of 6 self-named, across 4 distinct tickets and 4 distinct agents. Not a
fluke.

IMPACT: land invocations = 15, of which 7 were refused (47%). This guard
alone accounts for 6 of those 7. Each refusal costs a ~100-150s land
attempt plus an agent turn spent hand-resolving a ledger conflict the
playbook (section 10) tells it to resolve by "keep the newer state" -- a
rule that is mechanical when the only ticket involved is the one being
landed.

MECHANISM (hypothesis, implementer to confirm): main advances the landing
ticket's OWN ledger row while the agent works (the start transition, an
evidence row, a rapid-sweep close-debt row). The worktree then holds an
older-or-divergent copy of that same row. The guard compares the merge
result against main per ticket id and sees the landing ticket's row moving
backwards -- correctly detecting divergence, but wrongly classifying it as
a SIBLING regression. A ticket is not its own sibling.

FIX DIRECTION: exclude the landing ticket id from the sibling set, and
resolve its own row by the playbook's existing keep-the-newer-state rule
automatically. The guard must still refuse for genuine siblings -- that is
the T-1914 behaviour worth keeping.

POSITIVE CONTROL REQUIRED: (1) a must-still-fail case where a GENUINE
sibling's row would regress -> still refused; (2) a must-now-pass case
where only the landing ticket's own row diverges -> lands without hand
resolution. A fix that merely narrows until the observed 6 disappear,
without case (1), is unsound -- an exemption matching the normal case
disables the guard.
