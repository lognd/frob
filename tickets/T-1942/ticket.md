---
id: T-1942
title: Wire examined-sites as a third, additive WAIVE004 mass-invalidation guard
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
- src/frob/gates/_fix_engine_sync.py
- tickets/T-1964/**
- src/frob/gates/_arch.py
- src/frob/gates/_coverage_sites.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1964/**
  reason: T-1942 filed this residue ticket (deferred docs/modules/gates.md WAIVE004
    writeup, blocked by T-1958's lease) as part of its own Done report; its sharded-ledger
    bookkeeping needs to be in scope like T-1942's own (T-1819's tickets/<id>/** rule
    only covers the active ticket's own dir).
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_arch.py
  reason: 'Land-time LiveTrackerCited refusal: T-1921''s WIRE001 waivers on arch_examined_sites/attach_examined_sites/is_family_instrumented/site_examined
    cite follow_up=T-1942, fulfilled by this ticket''s wiring; re-pointing those 4
    citations to a successor (T-1965) is required to close T-1942.'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_coverage_sites.py
  reason: 'Land-time LiveTrackerCited refusal: T-1921''s WIRE001 waivers on arch_examined_sites/attach_examined_sites/is_family_instrumented/site_examined
    cite follow_up=T-1942, fulfilled by this ticket''s wiring; re-pointing those 4
    citations to a successor (T-1965) is required to close T-1942.'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_gates.py::TestWaive004ExaminedSitesGuard::test_examined_archgate_site_is_deleted
- tests/test_gates.py::TestWaive004ExaminedSitesGuard::test_uninstrumented_family_is_unchanged_from_today
- tests/test_gates.py::TestWaive004ExaminedSitesGuard::test_unexamined_archgate_site_refuses
- tests/test_gates.py::TestWaive004ExaminedSitesGuard::test_original_55_waiver_incident_shape_partial_examination_still_refuses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1921 built the per-site analysis-coverage substrate (GateStats.
examined_sites, frob.gates._coverage_sites) as substrate ONLY, per the
coordinator's explicit instruction: do not wire any automatic waiver-
retirement path on top of it in the same change -- that is exactly the
shape that let the falsified T-1579 escape (_rule_has_live_finding)
delete 55 live waivers.

Once family coverage is broad enough to be useful (see the sibling
residue ticket extending archgate-only coverage to strata/perf/graph/
vet), wire a THIRD, additive per-site check into
_drop_untrustworthy_mass_stale_candidates
(src/frob/gates/_fix_engine_sync.py) -- alongside, NEVER instead of,
the existing absolute/proportional mass-invalidation guards. A
candidate's own (file, rule) site must resolve True via
frob.gates._coverage_sites.site_examined for its rule's owning gate
family this run before the guard may even consider relaxing.

Still refuse on any uncertainty -- an unexamined or unknown-family site
must never be deletable, per the standing regression lock
(tests/test_gates.py::TestWaive004DegradedRunGuard::
test_mass_invalidation_with_live_finding_elsewhere_still_refuses).
Prove this ticket's own acceptance property with a new regression test:
fabricate a GateStats.examined_sites that covers SOME but not all sites
of a mass-stale rule, and show the guard still refuses for the
unexamined site.

This is deliberately separate, later, more carefully reviewed work --
do not fold it into the coverage-extension ticket or any other change
that touches _drop_untrustworthy_mass_stale_candidates for an unrelated
reason.