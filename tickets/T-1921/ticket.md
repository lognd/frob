---
id: T-1921
title: Per-site analysis-coverage substrate for WAIVE004 escape (T-1904 successor)
state: done
kind: feature
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_models.py
- src/frob/gates/_arch.py
- src/frob/gates/_coverage_sites.py
- src/frob/arch/__init__.py
- src/frob/arch/_models.py
- tests/test_gates.py
- tests/unit/gates/test_examined_sites.py
- docs/modules/gates.md
- docs/modules/arch.md
- docs/commands/check.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_fix_engine_sync.py
  reason: clear pre-declared scope to avoid lease collision at land time with concurrently-worked
    gates files; the future implementer will re-scope with frob ticket scope --add
    at start time per normal workflow
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: src/frob/gates/_models.py
  reason: clear pre-declared scope to avoid lease collision at land time with concurrently-worked
    gates files; the future implementer will re-scope with frob ticket scope --add
    at start time per normal workflow
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: src/frob/gates/__init__.py
  reason: clear pre-declared scope to avoid lease collision at land time with concurrently-worked
    gates files; the future implementer will re-scope with frob ticket scope --add
    at start time per normal workflow
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: tests/test_gates.py
  reason: clear pre-declared scope to avoid lease collision at land time with concurrently-worked
    gates files; the future implementer will re-scope with frob ticket scope --add
    at start time per normal workflow
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/gates/_models.py
  reason: 'per-site analysis-coverage substrate: GateStats gains examined_sites; populated
    for the ARCH family via analyze_project/arch_gate; a new gates/_coverage_sites.py
    enrichment module + query helper (avoids touching gates/__init__.py, leased by
    T-1929); new regression test file'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/gates/_arch.py
  reason: 'per-site analysis-coverage substrate: GateStats gains examined_sites; populated
    for the ARCH family via analyze_project/arch_gate; a new gates/_coverage_sites.py
    enrichment module + query helper (avoids touching gates/__init__.py, leased by
    T-1929); new regression test file'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/gates/_coverage_sites.py
  reason: 'per-site analysis-coverage substrate: GateStats gains examined_sites; populated
    for the ARCH family via analyze_project/arch_gate; a new gates/_coverage_sites.py
    enrichment module + query helper (avoids touching gates/__init__.py, leased by
    T-1929); new regression test file'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/arch/__init__.py
  reason: 'per-site analysis-coverage substrate: GateStats gains examined_sites; populated
    for the ARCH family via analyze_project/arch_gate; a new gates/_coverage_sites.py
    enrichment module + query helper (avoids touching gates/__init__.py, leased by
    T-1929); new regression test file'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/arch/_models.py
  reason: 'per-site analysis-coverage substrate: GateStats gains examined_sites; populated
    for the ARCH family via analyze_project/arch_gate; a new gates/_coverage_sites.py
    enrichment module + query helper (avoids touching gates/__init__.py, leased by
    T-1929); new regression test file'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_gates.py
  reason: 'per-site analysis-coverage substrate: GateStats gains examined_sites; populated
    for the ARCH family via analyze_project/arch_gate; a new gates/_coverage_sites.py
    enrichment module + query helper (avoids touching gates/__init__.py, leased by
    T-1929); new regression test file'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/unit/gates/test_examined_sites.py
  reason: 'per-site analysis-coverage substrate: GateStats gains examined_sites; populated
    for the ARCH family via analyze_project/arch_gate; a new gates/_coverage_sites.py
    enrichment module + query helper (avoids touching gates/__init__.py, leased by
    T-1929); new regression test file'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: docs/modules/gates.md
  reason: AFFECT001/COV001 doc-anchor closure for the changed ArchResult/GateStats/arch_gate
    public symbols
  actor: logan
  at: '2026-08-09'
- op: add
  glob: docs/modules/arch.md
  reason: AFFECT001/COV001 doc-anchor closure for the changed ArchResult/GateStats/arch_gate
    public symbols
  actor: logan
  at: '2026-08-09'
- op: add
  glob: docs/commands/check.md
  reason: AFFECT001 closure for analyze_project's memoization doc anchor
  actor: logan
  at: '2026-08-09'
evidence:
- tests/unit/gates/test_examined_sites.py::TestSiteExaminedSoundness::test_uninstrumented_family_reports_not_examined
- tests/unit/gates/test_examined_sites.py::TestSiteExaminedSoundness::test_instrumented_family_reports_true_for_a_known_site
- tests/unit/gates/test_examined_sites.py::TestSiteExaminedSoundness::test_instrumented_family_reports_false_for_an_unexamined_site
- tests/unit/gates/test_examined_sites.py::TestSiteExaminedSoundness::test_instrumented_but_empty_family_still_reports_false_for_any_site
- tests/unit/gates/test_examined_sites.py::TestIsFamilyInstrumented::test_absent_family_is_not_instrumented
- tests/unit/gates/test_examined_sites.py::TestIsFamilyInstrumented::test_present_empty_family_is_instrumented
- tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_archgate_examined_sites_include_a_real_python_file
- tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_archgate_examined_sites_exclude_an_unparseable_file
- tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_families_this_module_does_not_know_about_stay_absent
- tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_preserves_examined_sites_a_prior_caller_already_attached
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Filed from T-1904's own investigation (2026-08-09). T-1904's acceptance
criteria required per-SITE analysis-coverage tracking -- proof that the
specific waived (file, line, rule) site was actually re-analyzed in a
given run, not just that the rule produced a finding SOMEWHERE (the
already-falsified T-1579/_rule_has_live_finding shape that deleted 55
live waivers).

WHAT WAS INVESTIGATED. `GateReport`/`GateStats` (src/frob/gates/_models.py)
today carry only violations, waived violations, and per-gate counts/
timing/skipped-stage names -- there is no notion anywhere in the gate
substrate of "which files/sites did gate X actually visit this run".
Adding that honestly requires each gate FAMILY's own implementation (AST
walkers, native-backed checks, doc/registry scanners -- dozens of
independent modules under src/frob/gates/) to report its own examined-site
set, then plumbing that set through `run_gates`'s merge into `GateReport`,
then having `_drop_untrustworthy_mass_stale_candidates`
(src/frob/gates/_fix_engine_sync.py) consult it per candidate before ever
relaxing the count guards. That is a substrate change touching every gate
implementation, not a guard tweak -- exactly what T-1904's own body
predicted ("materially larger... a capability the gate substrate does not
currently have") and too large for a single ticket's scope.

WHAT T-1904 ITSELF DID. Re-applied the T-1579 branch's docstring note
(commit fc8f5bab9) onto `_drop_untrustworthy_mass_stale_candidates` in
`src/frob/gates/_fix_engine_sync.py`, on top of the landed refactor --
the "ALSO OWED" item T-1904's body named. No behavior changed; both count
guards (absolute and proportional) remain unconditional refusals, and the
standing regression lock
(`tests/test_gates.py::TestWaive004DegradedRunGuard::
test_mass_invalidation_with_live_finding_elsewhere_still_refuses`) is
untouched and still passing.

SCOPE FOR THIS TICKET. Design and land the per-site analysis-coverage
substrate:
- A shared `examined_sites` (or per-file) reporting contract every gate
  family can optionally populate, added to `GateStats`/`GateReport`.
- At least the WAIVE004-relevant gate families populate it for real
  (start with whichever families most of today's live `frob:waive`
  directives target -- arch/strata/perf/graph/vet, the exact families the
  55-waiver incident hit).
- `_drop_untrustworthy_mass_stale_candidates` gains a THIRD, additive
  check: a candidate's own site must appear in the examined set for its
  rule's owning gate family this run, in addition to (never instead of)
  the existing absolute/proportional guards -- still refuse on any
  uncertainty, per T-1904's acceptance test (a waiver whose site the
  analysis did not cover must never be deletable).
- Prove the acceptance property with a new regression test: fabricate a
  run that examined some but not all sites of a mass-stale rule and show
  the guard still refuses for the unexamined site.

Do not ship an automatic retirement path until the coverage substrate
itself has full field coverage across every gate family a live
`frob:waive` can target -- a partial substrate that "looks done" for a
few families is the same trap the 55-waiver incident was.