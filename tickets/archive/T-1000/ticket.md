---
id: T-1000
title: 'land: auto-accept strictly-improved test-count claims instead of ClaimDivergence
  refusal'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: T-0999
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_matching_claims_land_succeeds
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_test_count_refuses_land
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_strictly_improved_test_count_auto_accepts_and_rewrites_recap
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_lower_gate_error_count_than_claim_still_lands
designated_repro_test: null
acceptance:
- text: given a done ticket whose recorded claim is 0/0 and whose fresh re-run shows
    N/N passing, when it lands, then the land succeeds with the recap rewritten to
    N/N; given a fresh run with any failing test, the land still refuses
  evidence:
  - tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_strictly_improved_test_count_auto_accepts_and_rewrites_recap
  - tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_test_count_refuses_land
threat: null
component: null
---
Churn item 1 (~10 occurrences): every post-close touch stales the recap and land refuses with recorded 0/0 vs re-run N/N passing, cured identically each time by a manual done-report refresh + re-land. When the fresh count strictly improves (all passing, count >= recorded), land should auto-accept and rewrite the recap in the landing commit itself; genuine regressions (fewer passing or any failing) still refuse loudly.