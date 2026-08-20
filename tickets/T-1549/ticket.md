---
id: T-1549
title: 'Tier-A auto-fix: ClaimDivergence re-run via done-report recap'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_verify.py
- tests/unit/test_land_verify_claim_divergence_sentinel.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'narrowed to the actual fix site: the ClaimDivergence identity comparison
    in _land_verify.py; the auto-fix plan was replaced by a root-cause sentinel filter,
    see Done report'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_land_verify.py
  reason: 'narrowed to the actual fix site: the ClaimDivergence identity comparison
    in _land_verify.py; the auto-fix plan was replaced by a root-cause sentinel filter,
    see Done report'
  actor: logan
  at: '2026-08-19'
- op: remove
  glob: src/frob/gates/_fix_engine.py
  reason: not building the Tier-A handler; the fix lives entirely in _land_verify.py's
    identity comparison, see Done report for why
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/unit/test_land_verify_claim_divergence_sentinel.py
  reason: not building the Tier-A handler; the fix lives entirely in _land_verify.py's
    identity comparison, see Done report for why
  actor: logan
  at: '2026-08-19'
body_changes:
- mode: append
  reason: cross-reference T-2684, the manufacturing-side half of the same defect,
    per coordinator instruction
  actor: logan
  at: '2026-08-19'
  old_length: 344
  new_length: 1204
evidence:
- tests/unit/test_land_verify_claim_divergence_sentinel.py::TestQueueUnavailableSentinelIsExcludedFromDivergence::test_sentinel_alone_does_not_refuse
- tests/unit/test_land_verify_claim_divergence_sentinel.py::TestQueueUnavailableSentinelIsExcludedFromDivergence::test_real_new_in_scope_finding_still_refuses
- tests/unit/test_land_verify_claim_divergence_sentinel.py::TestQueueUnavailableSentinelIsExcludedFromDivergence::test_sentinel_plus_real_finding_still_refuses_on_the_real_one
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up from T-1531: a ClaimDivergence land refusal already has a documented manual recipe (re-run the ticket's done-report with its existing why text -- the recap re-measures the claim against current evidence). Wire a Tier-A handler that performs exactly that through the T-1262 verify-or-rollback transaction like every other handler here.

T-2684 cross-reference (coordinator-corroborated, 2026-08-19): this
ticket and T-2684 are two halves of one defect, not duplicates and not
independently sufficient. T-2684 fixes the MANUFACTURING site
(`frob.check._python._gates_error_result`, `src/frob/check/_python.py:
996`, hardcodes `Diagnostic(file="tickets.md", ...)` with no `code=`
whenever `GateError.QueueUnavailable` fires). This ticket (T-1549) fixes
the CONSUMING site (`_reverify_gate_findings_by_identity`,
`src/frob/tickets/_land_verify.py`) that let that identity-less
diagnostic count as a real new in-scope finding and refuse the land.
Confirmed as the root cause of four consecutive T-2666 land refusals
today, independently corroborated by the coordinator from the
manufacturing side. Neither ticket should be closed believing it fixed
the whole defect alone -- both halves are needed.