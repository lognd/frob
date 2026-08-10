---
id: T-2011
title: Wire perf/strata/graph/vet examined-sites reporters (T-1943) into a real WAIVE004
  consumer
state: done
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_sync.py
- tests/unit/test_waive004_perf_guard.py
- docs/modules/gates.md
- src/frob/gates/_coverage_sites.py
- src/frob/gates/_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_waive004_perf_guard.py
  reason: 'T-2011: new standalone test file for the perf-family WAIVE004 guard (tests/test_gates.py
    is under T-1959''s live lease)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-2011: WAIVE004 section needs its perf-family guard documented alongside
    T-1942''s archgate write-up'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_coverage_sites.py
  reason: 'T-2011 close is blocked by LiveTrackerCited: the WIRE001 waivers in these
    two files cite follow_up=T-2011 as their live tracker; must re-point to the T-2057
    successor before this ticket can close'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_arch.py
  reason: 'T-2011 close is blocked by LiveTrackerCited: the WIRE001 waivers in these
    two files cite follow_up=T-2011 as their live tracker; must re-point to the T-2057
    successor before this ticket can close'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_waive004_perf_guard.py::TestWaive004PerfExaminedSitesGuard::test_examined_perf_site_is_deleted
- tests/unit/test_waive004_perf_guard.py::TestWaive004PerfExaminedSitesGuard::test_unexamined_perf_site_refuses
- tests/unit/test_waive004_perf_guard.py::TestWaive004PerfExaminedSitesGuard::test_perf009_is_excluded_from_the_guard
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1943 extended frob.gates._coverage_sites' per-site examined-sites
substrate from archgate-only to perf/strata/graph/vet
(_perf_examined_sites/_strata_examined_sites/_graph_examined_sites/
_vet_examined_sites), matching T-1904's own investigation of which
families the 55-waiver incident actually hit. Same posture T-1921 took
for archgate: substrate only, no production caller wired in the same
change (the coordinator's standing instruction against doing both in
one diff, per the incident history).

T-1942 already wired archgate's examined-sites into
_drop_untrustworthy_mass_stale_candidates as
_drop_unexamined_archgate_candidates
(src/frob/gates/_fix_engine_sync.py). This ticket is the same shape for
the four new families: add an additive, per-site guard using
site_examined(stats, family, file) for each of "perf"/"strata"/"graph"/
"vet", alongside (never instead of) the existing archgate guard and the
absolute/proportional count guards. Refuse on any uncertainty, same
regression-lock posture as T-1942's own acceptance test.