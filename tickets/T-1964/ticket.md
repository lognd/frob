---
id: T-1964
title: docs/modules/gates.md WAIVE004 section needs T-1942 wiring writeup (blocked
  by T-1958 lease)
state: done
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/gates.md
- src/frob/gates/_fix_engine_sync.py
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine_sync.py
  reason: 'land refused to close: AFFECT001 waiver at src/frob/gates/_fix_engine_sync.py:953
    cites T-1964 as its live follow_up tracker; must re-point to the successor ticket
    in this same change or file one (filed T-2029)'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_gates.py::TestWaive004ExaminedSitesGuard::test_original_55_waiver_incident_shape_partial_examination_still_refuses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1942 wired frob.gates._coverage_sites' per-site examined-sites substrate
(T-1921) into fix_waive004_stale_waiver as a third, additive WAIVE004
mass-invalidation guard (_drop_unexamined_archgate_candidates). The change
needed a docs/modules/gates.md update at the WAIVE004 Tier-A fix-handler
section (AFFECT001's own affects()-closure target for
fix_waive004_stale_waiver), but docs/modules/gates.md's declared scope was
held by T-1958 (in-progress, a disjoint edit at #rule-catalog fixing
DOCENUM001) for the whole duration of T-1942's work -- frob ticket scope
--add refused with ScopeLeaseConflict, and per this repo's playbook, a
lease conflict is reported, not forced with --allow-cross-ticket.

T-1942 waived AFFECT001 on fix_waive004_stale_waiver's own diff instead of
forcing the scope conflict; this ticket is the deferred doc write. Add a
paragraph to the WAIVE004 Tier-A fix-handler section (near the existing
T-1579/T-1592/T-1904 incident writeup) describing:
- attach_examined_sites enriching the self-manufactured run_gates() report
  before candidates are derived
- _drop_unexamined_archgate_candidates as a third, additive guard stacked
  on top of the two existing ones, gated on rule id in the archgate
  family, granting nothing for any other family
- the regression test tests/test_gates.py::TestWaive004ExaminedSitesGuard,
  especially test_original_55_waiver_incident_shape_partial_examination_
  still_refuses (the original incident's shape narrowed to per-site)

Separately disclosed finding, NOT this ticket's scope: while investigating
why a frob:waive SCOPE001 comment placed in docs/modules/gates.md did not
suppress the SCOPE001 finding, direct reading of frob.graph.dsl and
frob.graph.__init__ (only markdown_anchors(doc_path, text) is called for
*.md files, never parse_directives) confirmed frob:waive directives are
NEVER parsed out of markdown files at all -- markdown_anchors only
extracts DESCRIBES/ENUMERATES/UNTIL/negexist-phrase edges. Every existing
`frob:waive ... -->` HTML comment already present in docs/**/*.md (e.g.
docs/modules/fuzz.md, docs/modules/deploy.md) is therefore dead prose,
never actually suppressing anything -- catalogued but not enforced, same
shape this repo has hit before. Filing as a separate finding rather than
fixing here since it is a real, repo-wide gap outside T-1942's declared
scope.