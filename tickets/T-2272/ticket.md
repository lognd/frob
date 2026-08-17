---
id: T-2272
title: main's _land.py uses _OrphanEvidenceCheckOutcome/_LAST_ORPHAN_EVIDENCE_OUTCOME
  with no class definition -- NameError crashes every frob ticket land
state: dropped
kind: bug
origin: human
created: '2026-08-17'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Every frob ticket land fails fleet-wide right now: 'ERROR: main: unhandled exception during dispatch: name _OrphanEvidenceCheckOutcome is not defined'. Confirmed via git show main:src/frob/tickets/_land.py | grep -n _OrphanEvidenceCheckOutcome -- 6 usages, zero class definition anywhere in the file or repo (git grep 'class _OrphanEvidenceCheckOutcome' returns nothing on main). The class DOES exist, fully implemented with a StrEnum def and the _LAST_ORPHAN_EVIDENCE_OUTCOME dict, in commit a98b65464 on branch t-2255 (not yet landed) -- that branch's fix (T-2255) is real and correct, but somehow only its USAGE sites (not its own definition) ended up on main, most likely via a bad three-way splice during a concurrent land race around 2026-08-17 03:00-03:20 (T-2256/T-2270/T-2255 lands all overlapped in that window). Fix: land T-2255 properly (bringing the missing class def onto main), or if T-2255 already landed partially, splice in just the missing class/dict definitions from a98b65464. Hit while trying to land T-2259 -- confirmed not caused by T-2259's own diff (agent_runner.py/test_worktree_guard.py only).

## Drop reason
- 2026-08-17: SYMPTOM RESOLVED, cause tracked elsewhere. Filed when main's _land.py carried 10 usages of _OrphanEvidenceCheckOutcome/_LAST_ORPHAN_EVIDENCE_OUTCOME with no definition, crashing every frob ticket land fleet-wide. T-2255's land (9fc8b80ef83c) restored the definition as a byproduct -- verified: main's _land.py now defines the class. The ROOT CAUSE is T-2274 (a concurrent land's 'record land commit' bookkeeping absorbed a dirty in-progress edit from the shared root and published broken partial state with no ticket/evidence trail); that ticket remains open and is where the real fix belongs. Keeping two critical tickets for a repaired symptom distorts prioritization. T-2273 is the duplicate of this one and is being dropped for the same reason.
