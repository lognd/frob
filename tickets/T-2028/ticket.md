---
id: T-2028
title: 'SCOPE002: docs/modules/gates.md anchor declaration + archgate test relocation,
  residue from T-2012'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/gates.md
- tests/unit/gates/test_examined_sites.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: 'T-2028: T-1964''s lease on docs/modules/gates.md landed (76b249405), scope
    declaration now free -- adding the anchor target for arch_examined_sites/arch_gate/attach_examined_sites/is_family_instrumented/site_examined
    per T-2012''s own SCOPE002 investigation'
  actor: logan
  at: '2026-08-10'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2012 closed the two SCOPE002 error-shaped gaps left over from T-1921
(tests/unit/gates/test_examined_sites.py, tests/test_arch_gate.py). One
real gap remains, not forced due to a live lease conflict:

docs/modules/gates.md is the frob:doc anchor target for
src/frob/gates/_arch.py::arch_examined_sites/arch_gate and
src/frob/gates/_coverage_sites.py::attach_examined_sites/
is_family_instrumented/site_examined -- the anchor CONTENT already
exists there (added by T-1921, docs/modules/gates.md#data-models and
#rule-catalog), this is purely a missing scope DECLARATION on the
ticket(s) that own those symbols. Add docs/modules/gates.md to scope
once T-1964's live lease on it clears.

Separately, decide relocate-vs-widen for two archgate-specific tests in
tests/unit/gates/test_examined_sites.py
(test_archgate_examined_sites_include_a_real_python_file,
test_archgate_examined_sites_exclude_an_unparseable_file) that carry a
frob:tests edge to src/frob/gates/_arch.py::arch_examined_sites, pulling
in _arch.py's own full test surface (tests/unit/test_arch_srp.py,
src/frob/gates/_waive.py) as SCOPE002 warnings whenever this file is in
a ticket's scope. T-2012's own investigation flagged widening scope that
far as disproportionate to a coverage-family-extension ticket; moving
those two tests into a file already scoped alongside _arch.py may be the
cleaner fix.
