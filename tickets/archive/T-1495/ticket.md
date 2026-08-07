---
id: T-1495
title: land crash-recovery/unwind can reset main past completed land commits (T-1464/T-1262
  eaten 2026-08-04)
state: done
kind: bug
origin: human
created: '2026-08-04'
priority: high
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits::test_foreign_commit_after_own_last_commit_refuses_instead_of_discarding
- tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits::test_no_foreign_commit_unwinds_to_the_merge_commit_not_pre_merge
designated_repro_test: null
threat: null
component: null
---
Incident 2026-08-04 (coordinator session): `frob ticket land T-1464` was SIGTERM-killed at the mandatory 540s timeout AFTER its land commits (T-1262 queue-drain + T-1464) were already on main, but before post-land verification finished. The NEXT land invocation (T-1259) performed `reset: moving to <pre-run-tip>` on main, silently DISCARDING both completed land commits (reflog HEAD@{2} at 10:0x). T-1464's code vanished from main while sibling ledger state later re-said done; recovered by coordinator cherry-pick of the orphaned land commit (b38d8517). Earlier in the same session the same pattern ate the T-1199 and T-1200 queue-drain commits plus an interleaved manual `frob ticket drop` commit (reflog resets to 0ecf9930), whose content only survived because later branch merges re-carried it.

Root-cause surface to fix (any/all):
1. A land run killed post-commit must not leave state that lets the next run treat COMPLETED commits as crash debris. _repair_stale_land_marker documents refuse-on-drift, yet a reset to the recorded pre-run tip happened while HEAD had advanced by two land commits -- find the actual reset path (queue-drain re-entry? SIGTERM finally-unwind?) and make it refuse or reconcile per-commit instead of resetting.
2. Queue-drain commits (other tickets' lands) must be durable the moment each one is committed -- a later failure in the SAME invocation (e.g. CrossTicketLeakage on the primary ticket) currently unwinds the whole run including unrelated drained lands (T-1199/T-1200 eaten by attempt-1/2 unwinds).
3. Interleaved manual ledger commits (a `frob ticket drop` between two land attempts) were also eaten by the run-level unwind; unwind must stop at the run's own first commit, never cross foreign commits.
4. Land duration routinely exceeds the 540s foreground guard; either checkpoint so a kill is safe at any instant, or split post-land verification into a resumable separate step.

Acceptance sketch: GIVEN a land invocation killed by SIGTERM after N land commits are on main WHEN any subsequent `frob ticket land` runs THEN no previously-committed land commit is removed from main's history, and any genuinely partial staging is either rolled forward or refused loudly with both shas named.