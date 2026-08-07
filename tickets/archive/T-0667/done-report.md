## Done report

Added SYS103 (SYS-COV, T-0667) to frob.strata._selfconform: coverage-totality
check that a FOREIGN file (no node's code= glob claims it) which
frob.vet._capability.scan_file_capabilities (T-0328's import/binding-aware
resolver, not a bare substring guess) observes ANY capability in fires --
"unbound-but-capable code is a hard failure" (T-0341 acceptance criterion 0).
A file bound to any node never fires SYS103 regardless of conformance
(SYS100/SYS101 already own the bound-file declared-vs-observed question).
A FOREIGN file with zero observed capabilities does not fire (no dangerous
effect escaping an obligation). Both T-0667 acceptance clauses are proved
directly: TestCoverageTotality.test_foreign_file_with_capability_fires_sys103
(clause 0, fires) and test_bound_file_discharges_sys103 (clause 1, silent).

SYS103 generalizes past SYS102's existing "unmodeled code" check, which is
hardcoded to _PACKAGE_ROOT ("src/frob", T-0211) and is therefore silently
vacuous on every non-frob repo -- SYS103 walks the WHOLE audited root by
default (test_fires_outside_src_frob_layout proves a capable, unbound file
OUTSIDE src/frob/ entirely still fires). It has no per-capability-kind
sub-target (whole FILE is unbound, not one kind of it) and is not in
_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES, so it takes the same bare-rule
waiver form SYS102 already uses (test_sys103_waivable_as_bare_rule).

REAL-GATE FINDING on frob's own model (as requested): running SYS103
unrestricted against design/frob.strata surfaced 264 real, currently-
unmodeled findings under tests/**, scripts/bump_version.py,
frob-core/src/lib.rs, and strata-core/src/lib.rs -- design/frob.strata has
only ever declared code=/may for src/frob/, so those trees were always
outside what the self-model claims to cover. Wiring SYS103 unrestricted
would have regressed the live SELFAUDIT001 gate (src/frob/gates/__init__.py,
out of this ticket's scope) from green to 264 errors on frob's own
`frob check --only sys`. Fixed by _coverage_totality_scan_prefix: SYS103
restricts itself to _PACKAGE_ROOT specifically when auditing frob's own
tree (matching SYS102's existing footprint there, zero regression,
confirmed: `frob check --only sys` now 0 errors both before and after),
while staying the full, unrestricted whole-root scan for every OTHER repo.
Filed T-1079 (model tests/**, scripts/**, frob-core, strata-core
in design/frob.strata to close the 264 real findings, or adopt a reasoned
exclusion) as the honest follow-up, referenced from docs/modules/strata.md's
"Known gap" section rather than silently narrowing SYS103's design.

Also flagged (resolved directly at coordinator close-out -- SYS103/SYS205 registered in the live rule set and the frob:enforces CHK-GATE-SYS103 edge added on check_self_conformance): docs/design/registry/check-coverage.yaml's
CHK-GATE-SYS100/101/102 registry cross-reference has no CHK-GATE-SYS103
sibling entry yet (docs/design/registry/** is out of scope) -- the
`frob:enforces CHK-GATE-SYS103` directive was likewise deliberately
omitted from check_self_conformance with an inline comment explaining why.

Not done / cuts: SYS103 does not attempt exact interface conformance,
purpose contracts, or waiver budgets (T-0341's other four acceptance
criteria) -- those are separate epic children, not this ticket's scope.

Gates: `frob check --ticket T-0667` clean across every stage group run
(gates-fast/gates-native/gates-security/lint/static all 0 errors) after
fixing one real DUP001 finding (a near-duplicate test rewritten to assert
a materially different claim) and refreshing the pre-work sweep. No
waivers needed for this ticket's own code.

### Changed
```
 docs/modules/strata.md                        |  90 ++++++++++++++
 src/frob/strata/__init__.py                   |   2 +
 src/frob/strata/_selfconform.py               | 165 +++++++++++++++++++++++++-
 tests/unit/strata/test_conform_eval_needle.py |   6 +
 tests/unit/strata/test_selfconform.py         | 132 ++++++++++++++++++++-
 tickets.md                                    | 160 ++++++++++++++++++++++++-
 6 files changed, 545 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_bound_file_discharges_sys103` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_capability_free_file_does_not_fire_sys103` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_fires_outside_src_frob_layout` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_sys103_waivable_as_bare_rule` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 1 error(s), 1893 warning(s), 421 waived
- error-findings: TICK006@tickets.md
