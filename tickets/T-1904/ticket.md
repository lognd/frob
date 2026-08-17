---
id: T-1904
title: Sound WAIVE004 escape needs per-site analysis-coverage tracking, not rule-level
  liveness (T-1579 successor)
state: done
kind: feature
origin: agent
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_sync.py
- tickets/T-1904/ticket.md
- tickets/T-1904/done-report.md
- tickets/T-1921/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine_sync.py
  reason: docstring reapply per ticket ALSO OWED note; own ticket dir files
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tickets/T-1904/ticket.md
  reason: docstring reapply per ticket ALSO OWED note; own ticket dir files
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tickets/T-1904/done-report.md
  reason: docstring reapply per ticket ALSO OWED note; own ticket dir files
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/gates/_fix_engine_sync.py
  reason: docstring reapply per ticket ALSO OWED note; own ticket dir files
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tickets/T-1904/ticket.md
  reason: docstring reapply per ticket ALSO OWED note; own ticket dir files
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tickets/T-1904/done-report.md
  reason: docstring reapply per ticket ALSO OWED note; own ticket dir files
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tickets/T-1921/ticket.md
  reason: residue draft filed from this ticket's own investigation (SCOPE001 precedent)
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_native001_degraded_run_deletes_nothing
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_skipped_stage_degraded_run_deletes_nothing
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_mass_invalidation_of_one_rule_deletes_nothing
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_mass_invalidation_with_live_finding_elsewhere_still_refuses
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_healthy_run_below_threshold_still_deletes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
SUPERSEDES the design T-1579 asked for. Filed 2026-08-09 from the T-1579 investigation; see T-1579 for the full trace.

WHAT WAS FALSIFIED, AND DO NOT RETRY IT. T-1579's literal ask -- 'let the auto-fix delete a waiver when the detector can PROVE the waived sites are gone' -- was already implemented once, as _rule_has_live_finding: a live finding of the target rule elsewhere in the same run was taken as proof the detector ran. It shipped, and during a real land it deleted 55 LIVE waivers, because a partially-degraded run (stale strata_core, all health checks reporting clean) still found SOME instances of a rule while missing the exact ones the waivers covered. It was reverted. A permanent regression test locks against reintroducing it:

  tests/test_gates.py::TestWaive004DegradedRunGuard::test_mass_invalidation_with_live_finding_elsewhere_still_refuses

Subsequent work did NOT re-enable an escape: T-1620 closed the two structural gaps that incident named (native-staleness detection missing strata_core, and the guard's sub-5 blind spot, via the proportional check) and its Done report says explicitly that re-enabling the escape was not its job. T-1886 only patched the proportional check's N=1 degenerate case. So today BOTH the absolute-count and proportional guards are unconditional refusals in _drop_untrustworthy_mass_stale_candidates -- that is the deliberately hardened post-incident state, NOT an oversight.

WHY 'RULE HAS A LIVE FINDING' IS UNSOUND. It proves the detector produced output SOMEWHERE. It does not prove the detector re-analyzed THE SITE THE WAIVER COVERS. A degraded run that analyzes 90% of the tree satisfies the former and violates the latter, which is exactly how 55 live waivers were deleted.

WHAT A SOUND VERSION REQUIRES. Per-site analysis-coverage tracking: proof that the specific waived site was actually re-analyzed in this run, propagated through each gate's optional native substrate so a degraded/partial run reports its own coverage honestly. That is materially larger than a guard tweak -- it is a capability the gate substrate does not currently have, and it is the ONLY basis on which the count guards should ever be relaxed.

ACCEPTANCE: do not implement an escape until per-site coverage exists. If this ticket is worked, the deliverable is the coverage-tracking substrate plus a proof obligation, not a loosened threshold. Any patch that relaxes the guard without per-site proof should be REFUSED at review, citing the 55-waiver incident.

ALSO OWED: branch t-1579 (commit fc8f5bab9) carries a docstring-only note of this finding in src/frob/gates/_fix_engine_sync.py that was never landed -- it conflicted with CRITICAL T-1900's edits to the same file. Re-apply that docstring on top of T-1900's landed fix, so the next agent meets this finding where they will actually look: in the code.

## Done report

Investigated T-1579's own falsified escape (`_rule_has_live_finding`,
reverted after deleting 55 live waivers) and the post-incident hardening
(T-1620, T-1886) that keeps both the absolute and proportional
mass-invalidation guards in `_drop_untrustworthy_mass_stale_candidates`
(src/frob/gates/_fix_engine_sync.py) unconditional refusals today.

WHAT A SOUND ESCAPE WOULD NEED, confirmed by reading the current gate
substrate: `GateReport`/`GateStats` (src/frob/gates/_models.py) carry no
notion of "which sites did gate X actually examine this run" -- only
violations, waived violations, and per-gate counts/timing/skipped-stage
names. Proving a specific waived SITE (not just its rule, somewhere) was
re-analyzed this run requires every gate family's own implementation to
report an examined-site set and that set to be plumbed through
`run_gates`'s merge -- a substrate change spanning dozens of independent
gate modules, not a guard tweak. This confirms T-1904's own body's
prediction and is materially larger than this ticket's scope. Per the
ticket's own stated legitimate outcome ("narrow to the piece that IS
soundly achievable... or file the residue explicitly"), I did NOT
implement an automatic escape -- doing so without per-site proof is
exactly the reviewed-and-refused pattern T-1904 names.

WHAT THIS TICKET DID SHIP: the "ALSO OWED" item from T-1904's own body --
re-applied the T-1579 branch's (commit fc8f5bab9) docstring paragraph onto
`_drop_untrustworthy_mass_stale_candidates` in
src/frob/gates/_fix_engine_sync.py, on top of the landed refactor of that
function (it had been dropped by a conflict with T-1900's edits to the
same file and never landed). The added paragraph documents, at the exact
code site future agents will read, why no live-finding-shaped escape
exists, what a sound one requires, and points at the standing regression
lock. No behavior changed: both count guards remain unconditional
refusals, verified below.

WHAT I DID NOT ACHIEVE: the per-site analysis-coverage tracking substrate
itself. Filed as T-1921 (residue ticket; will renumber at land)
with the investigation findings above and a concrete scope: add an
examined-sites reporting contract to GateStats/GateReport, populate it
for the gate families the 55-waiver incident actually hit (arch/strata/
perf/graph/vet), and add a THIRD, additive per-site check to
`_drop_untrustworthy_mass_stale_candidates` alongside (never instead of)
today's absolute/proportional guards, proven by a new regression test
that a partially-examined mass-stale rule still refuses for its
unexamined sites.

Verification: the standing regression lock
(tests/test_gates.py::TestWaive004DegradedRunGuard, 5 tests, including
`test_mass_invalidation_with_live_finding_elsewhere_still_refuses`) passes
unchanged -- the acceptance property ("a waiver whose site the analysis
did not cover must never be deletable") already held before this change
via the unconditional refusal T-1592/T-1620/T-1886 built, and this ticket
leaves that refusal exactly as it was, now with the docstring explaining
why. `ruff check src/frob/gates/_fix_engine_sync.py` clean.
`frob check --ticket T-1904 --only gates-fast`: gate:SCOPE and gate:PRE
clean (0 errors); the two remaining gate families with errors
(gate:REG, gate:SUPPRESS) are pre-existing, repo-wide findings unrelated
to this ticket's touched file (.claude/hooks/*.py suppression drift,
docs/design/registry/*.yaml dangling dispositions) -- confirmed by their
file paths not matching this ticket's scope.

### Changed
```
 tickets/T-1904/ticket.md           | 43 ++++++++++++++++++++-
 tickets/T-1921/ticket.md | 79 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 121 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 3 error(s), 827 warning(s), 697 waived
- error-findings: REG002@docs/design/registry/check-coverage.yaml, SUPPRESS001@.claude/hooks/frob-suggest.py, SUPPRESS001@.claude/hooks/frob-timeout-guard.py
