+++
id = "01M1T07NY8MSCC3E46QDWEF5H8"
title = "waived frob:tests must still record its claimed kind"
type = "task"
category = "todo"
priority = "low"
parent = "01M1T07NXGXQ1VDNZ4FWF10TGF"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T22:22:22Z"
aliases = ["T-4040"]
labels = ["v1-cluster:C4a", "triage:accepted"]
scope = ["src/frob/graph/dsl.py"]

[[links]]
kind = "blocked-by"
target = "01M1T07NXGXQ1VDNZ4FWF10TGF"

[[acceptance]]
text = "given a frob:tests directive waived for a tooling reason, when the waiver is recorded, then it carries the same kind= the directive would have claimed if bound"
bound = false

[[acceptance]]
text = "given T-4016 lands and the waiver is lifted, when the directive re-binds, then its actual kind is checked against the kind recorded at waiver time"
bound = false
+++

Item 7. DOWNSTREAM OF T-4016 (already filed: the TS walker emits no symbol for describe()/it() call expressions, so no frob:tests directive can ever bind a vitest test). The waiver this item is about exists BECAUSE of T-4016's gap -- a frob:tests edge for TS/vitest test code cannot bind (no symbol to bind to), so it gets waived for a TOOLING reason instead. This item is genuinely downstream and should not be started before T-4016 lands, though it is not identical work -- filed with blocked_by=T-4016 to record the dependency.

VERIFIED: git grep for kind= alongside frob:waive TEST-family rules found no existing mechanism recording what KIND of test evidence a waived claim asserted. _TESTS_KINDS (src/frob/graph/dsl.py: unit/integration/e2e/property) exists for a BOUND frob:tests edge, but a WAIVED one carries no equivalent.

FINDING THIS WOULD HAVE CAUGHT: a frob:tests claim waived for a tooling reason (the TS-walker gap, or any similar binding failure) states WHY the evidence is invisible but not WHAT KIND of evidence it was claiming -- so nobody notices later that the waived tests are UNIT-shaped where the original claim was INTEGRATION-shaped, silently downgrading the actual coverage claim with no visible signal. Proposed: a waived frob:tests directive must still carry its intended kind= (unit/integration/e2e/property), recorded alongside the waiver reason, so once the underlying tooling gap (T-4016) closes and the waiver is lifted, the re-bound evidence can be checked against the SAME kind it originally claimed rather than whatever kind the newly-working binding happens to produce.
