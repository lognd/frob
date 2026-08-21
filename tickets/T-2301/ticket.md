---
id: T-2301
title: Relocate two archgate SCOPE002-widening tests out of test_examined_sites.py
state: done
kind: docs
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/gates/test_examined_sites.py
- tests/test_arch_gate.py
- src/frob/gates/_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_arch_gate.py::TestArchExaminedSites::test_archgate_examined_sites_include_a_real_python_file
- tests/test_arch_gate.py::TestArchExaminedSites::test_archgate_examined_sites_exclude_an_unparseable_file
- tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_families_this_module_does_not_know_about_stay_absent
- tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_preserves_examined_sites_a_prior_caller_already_attached
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Residue from T-2028/T-2012. Two tests in tests/unit/gates/test_examined_sites.py (TestAttachExaminedSites.test_archgate_examined_sites_include_a_real_python_file, test_archgate_examined_sites_exclude_an_unparseable_file) carry a frob:tests edge to src/frob/gates/_arch.py::arch_examined_sites, which pulls in _arch.py's own full test surface (tests/unit/test_arch_srp.py, src/frob/gates/_waive.py) as SCOPE002 warnings whenever tests/unit/gates/test_examined_sites.py is in a ticket's scope. T-2012's investigation flagged widening scope that far as disproportionate to a coverage-family-extension ticket. Decide relocate-vs-widen: moving those two tests into tests/test_arch_gate.py (already scoped alongside _arch.py, carries other frob:tests edges to it) may be the cleaner fix, but requires updating the two frob:tests directives in src/frob/gates/_arch.py:182-183 to point at the new location -- hence _arch.py itself needs to be in this follow-up's scope, unlike T-2028's own narrower scope.