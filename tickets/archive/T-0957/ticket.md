---
id: T-0957
title: 'ledger regression: T-0700/T-0702 show state:queued despite landed, tested
  code'
state: dropped
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while working T-0703: on origin/main HEAD (b3589c3e), `tickets.md` shows T-0700 ("strata grammar: access modes + shared-resource/lease declarations for contention proofs") and T-0702 ("strata grammar: demand declarations (users/rate) with flow propagation and fan-in summation") both as `state: queued`, `blocked_by=[]`, with no done-report or evidence -- yet their grammar is fully implemented, documented, and consumed: `src/frob/strata/_access.py` (SYS204, AccessMode, node_access_declarations, resource_contention_violations) and `src/frob/strata/_facts.py::FactBase.aggregate_demand`/`AggregateDemand` both exist, have full module docstrings referencing "T-0700"/"T-0702" in the past tense, and are covered by passing tests (`tests/unit/strata/test_access.py`, `tests/unit/strata/test_demand.py`). `git log --oneline` on origin/main shows commits "feat(tickets): land T-0700 ..." and a T-0702 close/land commit chain as ancestors of the current tip.

This blocked a dependent ticket (T-0703, whose declared `blocked_by=['T-0700','T-0702']`) from running `frob ticket start`/`frob ticket sweep` at all, even though the actual prerequisite code was already present and usable -- had to build and verify T-0703 against the real code while leaving its own ledger `start`/`sweep`/`close` CLI calls unresolved pending this investigation.

Likely root cause: the same land-splice/stale-ledger regression class already tracked (see MEMORY "Land splice regression" -- frob ticket land dropping/regressing sibling in-progress or closed ledger blocks; T-0577 was a partial fix). Someone with land-tooling context should: (1) confirm via git history whether T-0700/T-0702's close/done-report content was reverted by a later land/merge, (2) restore their `state: closed` + evidence + done-report blocks (or re-run their own close flow) so the ledger matches the code that is actually in the tree, and (3) check whether other REL2xx/SYS2xx tickets in the T-0331 epic have the same regression.

## Drop reason
- 2026-07-27: false alarm: compared against stale origin/main; local main ledger is correct