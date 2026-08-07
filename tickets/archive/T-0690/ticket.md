---
id: T-0690
title: 'frob:raises directive: declared exception surfaces at FFI boundaries, cross-checked
  where statically visible'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
blocked_by:
- T-0686
parent: T-0685
tier: ticket
sprint: null
scope:
- src/frob/graph/dsl.py
- src/frob/gates/**
- src/frob/arch/**
- strata-core/**
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: add FFI001/FFI002 evidence tests to tests/test_gates.py
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates.py::TestFfiBoundaryGate::test_pyo3_drift_fires_ffi001
- tests/test_gates.py::TestFfiBoundaryGate::test_pyo3_declared_matches_no_drift
- tests/test_gates.py::TestFfiBoundaryGate::test_ctypes_call_without_declaration_fires_ffi002
- tests/test_gates.py::TestFfiBoundaryGate::test_ctypes_call_with_empty_declaration_clean
designated_repro_test: null
acceptance:
- text: GIVEN a pyo3 function whose Rust side constructs PyValueError but whose frob:raises
    omits it WHEN the gate runs THEN a drift error names both sides; GIVEN a ctypes
    boundary with no frob:raises THEN a finding demands the declaration
  evidence:
  - tests/test_gates.py::TestFfiBoundaryGate::test_pyo3_drift_fires_ffi001
  - tests/test_gates.py::TestFfiBoundaryGate::test_ctypes_call_without_declaration_fires_ffi002
threat: null
component: null
---
User mandate: propagate exception info across the FFI boundary and enforce declaration wherever possible. Three tiers by static visibility: (1) OUR pyo3 crates (strata_core/frob_core): the Rust side IS visible -- PyResult error constructions, explicit PyErr types, panic! -> pyo3 PanicException; parse the Rust side (Rust adapter already parses these crates) and CROSS-CHECK the Python-side frob:raises declaration against the observed Rust-side set; drift = gate error. (2) ctypes/extern-C: no exception propagation exists (errno/return codes; a C++ exception crossing extern C is terminate/UB -- flag that pattern in our C++ as an ERROR); declaration is the only truth -- enforce every ctypes boundary in our repos carries frob:raises (declaring the empty set + errno convention is valid). (3) third-party compiled modules: declaration optional; Unknown otherwise. Grammar mirrors frob:deprecated (T-0576 precedent); register rule ids; docs same change.