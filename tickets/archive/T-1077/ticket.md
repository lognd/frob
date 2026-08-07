---
id: T-1077
title: 'arch: split remaining gate families out of src/frob/gates/__init__.py (T-0395/T-1072
  remainder)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_todo002_unbound_directive
- tests/test_gates.py::TestCoverageGate::test_todo001_bare_comment_in_touched_file
- tests/test_gates.py::TestCoverageGate::test_todo002_edge_to_closed_ticket
- tests/test_gates.py::TestCoverageGate::test_todo003_fires_after_version_bump_since_deferral_landed
- tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_no_version_bump_since_deferral
- tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_ticket_closes
- tests/test_gates.py::TestFmt001Gate::test_directive_run_over_limit_flagged
- tests/test_gates.py::TestFmt001Gate::test_ordinary_long_comment_not_flagged
- tests/test_gates.py::TestFmt001Gate::test_long_code_line_not_flagged
- tests/test_gates.py::TestFmt001Gate::test_untouched_line_not_flagged
- tests/test_gates.py::TestFmt001Gate::test_short_directive_not_flagged
designated_repro_test: null
threat: null
component: null
---
Filed from T-1072's partial land: T-1072 extracted only the WAIVE/PLACE001
family (`src/frob/gates/_waive.py`, 1972 lines) out of
`src/frob/gates/__init__.py`, taking it from 12047 to 10159 lines --
still far above the 800-line large-file threshold (docs/modules/gates.md),
still the repo's largest file by a wide margin. This ticket covers the
remaining gate families still resident in `__init__.py`, following the
exact same pattern (private sibling module per cohesive family,
`__init__.py` re-imports and re-exports unchanged, `frob:*` directives
travel with the moved code, DRIFT002/AFFECT001 references in
tests/docs updated to the new module path):

- COV00x (coverage_gate + _cov001.._cov007 helpers) -- large, likely its
  own tier
- TODO00x / FMT00x
- DEBT00x / DEPR00x (deprecated_gate)
- SCOPE00x / PREWORK (prework_gate)
- INV00x (invariant_gate, inv003_gate)
- TEST00x family (test_gate + _test004.._test013 helpers) -- large
- DECISIONS (decisions_gate)
- TICK00x (tickets_gate)
- COMPLIANCE00x (compliance_gate)
- SYS00x / DOC00x (sys_gate, selfaudit)
- DUP00x (dup_gate)
- REL00x (release_gate)
- FUZZ00x (fuzz_gate)
- DOCLINK/DOCANCHOR (doclink_gate, docanchor_gate)
- PERF (perf_gate)
- the `run_gates` orchestration spine (`_GateInputs`, `_build_jobs`,
  `_run_combined_jobs`, etc.) -- likely stays in `__init__.py` as the
  package's true entry point, but should be re-measured once everything
  else has moved out from under it.

Plan carefully before moving code; verify with the full gates test suite
after each chunk; land incrementally, same discipline T-1072 used.