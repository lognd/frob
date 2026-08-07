---
id: T-0774
title: 'land: preflight-simulate EvidenceScopeUnbound (covers_scope) pre-merge to
  close the residual fail-after-merge class'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestScopeUnboundPreflightBeforeMerge::test_scope_unbound_refused_pre_merge_no_commits_created
- tests/test_ticket_land.py::TestScopeUnboundPreflightBeforeMerge::test_covers_scope_true_still_lands_normally
designated_repro_test: null
acceptance:
- text: GIVEN a ticket whose evidence does not cover its scope WHEN frob ticket land
    runs THEN it refuses before creating any merge/finalize commit, naming the uncovered
    scope, with git log unchanged
  evidence:
  - tests/test_ticket_land.py::TestScopeUnboundPreflightBeforeMerge::test_scope_unbound_refused_pre_merge_no_commits_created
  - tests/test_ticket_land.py::TestScopeUnboundPreflightBeforeMerge::test_covers_scope_true_still_lands_normally
threat: null
component: null
---
T-0763 moved unbound-acceptance closeability preflight before merge, but EvidenceScopeUnbound (the covers_scope D-05 check) still runs post-merge because it needs the obligation graph from frob.gates, which frob.tickets cannot import (dependency is injected via the covers_scope callable parameter -- verified by the T-0763 reviewer). Residual: a ticket with bound-but-scope-uncovering evidence still fails AFTER the merge commit exists. Fix direction: have the CLI layer (frob.app.ticket_runner, which CAN import frob.gates) pass covers_scope into a pre-merge preflight simulation as well, or restructure land() to compute the post-merge graph in a temporary index without committing. Filed per T-0763 reviewer recommendation.