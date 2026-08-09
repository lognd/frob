---
id: T-1904
title: Sound WAIVE004 escape needs per-site analysis-coverage tracking, not rule-level
  liveness (T-1579 successor)
state: queued
kind: feature
origin: agent
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
SUPERSEDES the design T-1579 asked for. Filed 2026-08-09 from the T-1579 investigation; see T-1579 for the full trace.

WHAT WAS FALSIFIED, AND DO NOT RETRY IT. T-1579's literal ask -- 'let the auto-fix delete a waiver when the detector can PROVE the waived sites are gone' -- was already implemented once, as _rule_has_live_finding: a live finding of the target rule elsewhere in the same run was taken as proof the detector ran. It shipped, and during a real land it deleted 55 LIVE waivers, because a partially-degraded run (stale strata_core, all health checks reporting clean) still found SOME instances of a rule while missing the exact ones the waivers covered. It was reverted. A permanent regression test locks against reintroducing it:

  tests/test_gates.py::TestWaive004DegradedRunGuard::test_mass_invalidation_with_live_finding_elsewhere_still_refuses

Subsequent work did NOT re-enable an escape: T-1620 closed the two structural gaps that incident named (native-staleness detection missing strata_core, and the guard's sub-5 blind spot, via the proportional check) and its Done report says explicitly that re-enabling the escape was not its job. T-1886 only patched the proportional check's N=1 degenerate case. So today BOTH the absolute-count and proportional guards are unconditional refusals in _drop_untrustworthy_mass_stale_candidates -- that is the deliberately hardened post-incident state, NOT an oversight.

WHY 'RULE HAS A LIVE FINDING' IS UNSOUND. It proves the detector produced output SOMEWHERE. It does not prove the detector re-analyzed THE SITE THE WAIVER COVERS. A degraded run that analyzes 90% of the tree satisfies the former and violates the latter, which is exactly how 55 live waivers were deleted.

WHAT A SOUND VERSION REQUIRES. Per-site analysis-coverage tracking: proof that the specific waived site was actually re-analyzed in this run, propagated through each gate's optional native substrate so a degraded/partial run reports its own coverage honestly. That is materially larger than a guard tweak -- it is a capability the gate substrate does not currently have, and it is the ONLY basis on which the count guards should ever be relaxed.

ACCEPTANCE: do not implement an escape until per-site coverage exists. If this ticket is worked, the deliverable is the coverage-tracking substrate plus a proof obligation, not a loosened threshold. Any patch that relaxes the guard without per-site proof should be REFUSED at review, citing the 55-waiver incident.

ALSO OWED: branch t-1579 (commit fc8f5bab9) carries a docstring-only note of this finding in src/frob/gates/_fix_engine_sync.py that was never landed -- it conflicted with CRITICAL T-1900's edits to the same file. Re-apply that docstring on top of T-1900's landed fix, so the next agent meets this finding where they will actually look: in the code.