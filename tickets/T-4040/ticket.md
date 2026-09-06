---
id: T-4040
title: waived frob:tests must still record its claimed kind
state: queued
kind: feature
origin: agent
created: '2026-09-06'
priority: low
blocked_by:
- T-4016
parent: T-4036
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a frob:tests directive waived for a tooling reason, when the waiver
    is recorded, then it carries the same kind= the directive would have claimed if
    bound
  evidence: []
- text: given T-4016 lands and the waiver is lifted, when the directive re-binds,
    then its actual kind is checked against the kind recorded at waiver time
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Item 7. DOWNSTREAM OF T-4016 (already filed: the TS walker emits no symbol for describe()/it() call expressions, so no frob:tests directive can ever bind a vitest test). The waiver this item is about exists BECAUSE of T-4016's gap -- a frob:tests edge for TS/vitest test code cannot bind (no symbol to bind to), so it gets waived for a TOOLING reason instead. This item is genuinely downstream and should not be started before T-4016 lands, though it is not identical work -- filed with blocked_by=T-4016 to record the dependency.

VERIFIED: git grep for kind= alongside frob:waive TEST-family rules found no existing mechanism recording what KIND of test evidence a waived claim asserted. _TESTS_KINDS (src/frob/graph/dsl.py: unit/integration/e2e/property) exists for a BOUND frob:tests edge, but a WAIVED one carries no equivalent.

FINDING THIS WOULD HAVE CAUGHT: a frob:tests claim waived for a tooling reason (the TS-walker gap, or any similar binding failure) states WHY the evidence is invisible but not WHAT KIND of evidence it was claiming -- so nobody notices later that the waived tests are UNIT-shaped where the original claim was INTEGRATION-shaped, silently downgrading the actual coverage claim with no visible signal. Proposed: a waived frob:tests directive must still carry its intended kind= (unit/integration/e2e/property), recorded alongside the waiver reason, so once the underlying tooling gap (T-4016) closes and the waiver is lifted, the re-bound evidence can be checked against the SAME kind it originally claimed rather than whatever kind the newly-working binding happens to produce.
