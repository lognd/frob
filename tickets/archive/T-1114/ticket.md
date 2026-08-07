---
id: T-1114
title: 'arch: abstraction-opportunity gates package extraction (T-1082 remainder)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestDebtGate::test_debt001_malformed_directive_is_reported
- tests/test_gates.py::TestDeprecatedGate::test_depr001_malformed_directive_is_reported
- tests/unit/test_design_invariants.py::TestInv007::test_forbidden_import_fires
- tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_pending_phrasing_is_binding
designated_repro_test: null
threat: null
component: null
---
Filed from T-1082's partial land: T-1082 consolidated the cross-cutting
`_tracked_files`/`git ls-files` duplicate (5 gate modules --
_opaque.py, _exclude_hazard.py, _refs.py, _secrets.py,
_cve_fingerprint_scan.py -- each defining a byte-for-byte identical
private helper) into one shared `frob.gates._tracked_files.tracked_files`
and inlined every call site, clearing that specific abstraction-
opportunity cluster entirely. It did NOT attempt the remaining 29
findings T-1082 was filed to cover (19 in gates/__init__.py, 1 each in
_baseline.py, _cve_fingerprint_scan.py, _docblocks.py,
_fmt_directives.py, _gate_cache.py, _waive.py/_waive_lease.py,
invariants.py, 3 in _pii_structural.py), nor the wider
`_tracked_python_files`-shaped duplication T-1082 named as likely
undercounted (_walk_lint.py, _pii_structural/_tracked.py, _docblocks.py,
_docptr.py all define their own git-ls-files-with-suffix-filter variant),
nor the new small cluster the consolidation itself introduced (the new
`frob.gates._tracked_files.tracked_files` now shares a `(Path, str) ->
tuple[str, ...]` signature with 4 functions in
src/frob/dup/_pipeline/_callgraph.py -- out of gates/ scope entirely).

Re-measure `uv run frob check --only arch --json` scoped to
`src/frob/gates/` before starting; other tickets may have landed in the
interim and changed the count from the 29 this ticket, and its
predecessor T-1082, were filed against.