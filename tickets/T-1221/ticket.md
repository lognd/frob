---
id: T-1221
title: 'rust: capability-scan resolver in frob_core -- import table + alias propagation
  + candidate resolution'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1219
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/vet/_capability.py
- frob-core/**
- tests/unit/test_capability_native.py
- docs/modules/vet.md
- docs/modules/dup.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_capability_native.py
  reason: 'the resolver mirrors frob.vet._capability_python''s semantics (coordinator''s
    own brief: read it, agree on what a capability site is) -- golden-parity tests
    belong alongside the T-1220 precedent''s own test file, and docs/modules/vet.md
    is where the public-api frob:doc anchor for scan_python_capabilities must land'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/vet.md
  reason: 'the resolver mirrors frob.vet._capability_python''s semantics (coordinator''s
    own brief: read it, agree on what a capability site is) -- golden-parity tests
    belong alongside the T-1220 precedent''s own test file, and docs/modules/vet.md
    is where the public-api frob:doc anchor for scan_python_capabilities must land'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/dup.md
  reason: kernel-export-count prose in dup.md's frob-core kernels section must be
    updated in the same change as adding scan_python_capabilities, same as T-1220's
    own precedent
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001 required declaring test_capability_native.py's fs.write/fs.read/exec
    capabilities on the testsuite node, same as T-1220's own precedent for this file
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_import_alias_and_scope_shadowing
- tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_functools_partial_and_literal_dict_dispatch
- tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_dynamic_dispatch_is_unresolved_not_silently_dropped
- tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_this_repos_own_capability_python_module_matches
designated_repro_test: null
acceptance:
- text: 'GIVEN vet/_capability.py''s 5 Python recursions per file (import table walk,
    alias walk, candidate walk, comment spans, docstring spans -- 37 pct of sys, est
    ~8s native) are self-contained per-file functions of file bytes + a static needle
    registry WHEN a frob_core export scan_python_capabilities(source: bytes) -> (candidates,
    spans) replaces the Python recursions THEN sys''s capability-scan share drops
    correspondingly and the vet CLI path speeds up proportionally'
  evidence:
  - tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_import_alias_and_scope_shadowing
  - tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_functools_partial_and_literal_dict_dispatch
  - tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_dynamic_dispatch_is_unresolved_not_silently_dropped
  - tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_unparseable_source_returns_empty_not_a_crash
  - tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_this_repos_own_capability_python_module_matches
threat: null
component: null
---
Root cause and target: Rust-migration candidate #2 from the report, MEDIUM-HIGH feasibility. Depends on candidate #1's tree access (the tree-extraction kernel), so this is a natural second crate export once that lands. Self-contained semantics make this a clean FFI boundary; respect FFI001/FFI002.