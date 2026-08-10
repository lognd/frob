---
id: T-1942
title: Wire examined-sites as a third, additive WAIVE004 mass-invalidation guard
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
