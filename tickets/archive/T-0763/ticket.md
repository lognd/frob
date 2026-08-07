---
id: T-0763
title: 'CRITICAL friction: frob ticket land must run closeability preflight BEFORE
  merging, not fail-after-merge leaving a commit to reset'
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: critical
parent: T-0577
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestUnboundAcceptancePreflightBeforeMerge::test_unbound_acceptance_refused_pre_merge_no_commits_created
designated_repro_test: null
acceptance:
- text: GIVEN a ticket with an unbound acceptance criterion WHEN frob ticket land
    runs THEN it errors naming the unbound criterion and creates NO merge/finalize
    commit (git log unchanged), not fail-after-merge
  evidence:
  - tests/test_ticket_land.py::TestUnboundAcceptancePreflightBeforeMerge::test_unbound_acceptance_refused_pre_merge_no_commits_created
threat: null
component: null
---
Coordinator friction, 15+ occurrences 2026-07-22: frob ticket land MERGES the worktree into main FIRST, then attempts the close, and when close fails (AcceptanceUnbound, EvidenceScopeUnbound, InvalidTransition done->done) it leaves a finalize/merge commit the coordinator must `git reset --hard HEAD~1` before every retry. The close preconditions (acceptance bound, evidence covers scope, state is in-progress) are all knowable BEFORE the merge. Fix: land runs a CLOSEABILITY PREFLIGHT (all close checks, dry) BEFORE the merge/finalize; if it would fail, land errors with the specific unmet precondition and touches NOTHING -- no merge commit to unwind, no reset dance. Only after preflight passes does it merge+finalize+close. This turns every failed land from a 3-command recovery into a one-line actionable error.