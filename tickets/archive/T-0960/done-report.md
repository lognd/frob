## Done report

Changed:
- src/frob/strata/_process_bounds.py (new module: REL390/REL391 kernel-
  interface-classification pair, REL392/REL393 process-resource-bounds
  pair, ProcessBoundsReport/ProcessBoundsViolation,
  check_process_bounds_obligations)
- src/frob/strata/__init__.py (re-export the new module's public symbols)
- src/frob/gates/__init__.py (_KNOWN_GATE_RULES: added REL390/REL391/
  REL392/REL393 only -- T-0961 is concurrently registering the separate
  REL26x-38x backlog batch in the same frozenset)
- docs/strata/reliability.md (new "REL39x: KERNEL-INTERFACE +
  PROCESS-BOUNDS (T-0960)" section: obligation description, surface
  vocabulary, grammar-data-ceiling honesty note, waiver channel, See-also
  entries for the module and its test file)
- tests/unit/strata/test_process_bounds.py (new, 12 tests: missing/
  clean/waived per obligation pair, plus unproven/discharged/uncheckable
  per obligation pair)
- docs/design/registry/system-design.yaml (re-pointed both T-0960 rows'
  disposition from deferred:T-0960 to handled_by:REL390 and
  handled_by:REL392 respectively)

Scope was widened from the ticket's original two-path declaration
(src/frob/strata/_process_bounds.py, docs/strata/reliability.md) via
`frob ticket scope --add` to also cover src/frob/strata/__init__.py,
tests/unit/strata/test_process_bounds.py, src/frob/gates/__init__.py, and
docs/design/registry/system-design.yaml -- the obligation-family pattern
this ticket was dispatched to follow (mirroring T-0646/T-0919) requires
wiring, tests, and known-rule-id registration beyond the two files
originally listed; reason recorded in the ticket's scope_changes audit
trail.

Design note: both obligation pairs are declaration-and-proof checks over
strata's own host/deploy vocabulary (KernelModel.nodes / bound source
text), not runtime kernel introspection -- this cannot observe an actual
running process's cgroup file or an actual syscall's real classification,
only whether a Node attr declaration and its bound-code evidence exist.
This mirrors the same honesty ceiling REL201/REL222/REL231/REL261/REL301/
REL311 already establish for their own dimensions; disclosed directly in
the module and doc-section GRAMMAR-DATA CEILING notes rather than silently
overclaiming runtime enforcement.

Evidence:
- tests/unit/strata/test_process_bounds.py::TestMissingInterfaceClassification::test_kernel_interface_node_without_classification_fires
- tests/unit/strata/test_process_bounds.py::TestMissingInterfaceClassification::test_discharged_and_non_kernel_interface_nodes_clean
- tests/unit/strata/test_process_bounds.py::TestMissingInterfaceClassification::test_waiver_discharges_finding
- tests/unit/strata/test_process_bounds.py::TestUnprovenInterfaceClassification::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_process_bounds.py::TestUnprovenInterfaceClassification::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_process_bounds.py::TestUnprovenInterfaceClassification::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
- tests/unit/strata/test_process_bounds.py::TestMissingProcessBounds::test_deployed_process_node_without_bounds_fires
- tests/unit/strata/test_process_bounds.py::TestMissingProcessBounds::test_discharged_and_non_deployed_process_nodes_clean
- tests/unit/strata/test_process_bounds.py::TestMissingProcessBounds::test_waiver_discharges_finding
- tests/unit/strata/test_process_bounds.py::TestUnprovenProcessBounds::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_process_bounds.py::TestUnprovenProcessBounds::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_process_bounds.py::TestUnprovenProcessBounds::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
All 12 observed passing: `uv run pytest tests/unit/strata/test_process_bounds.py -p no:cacheprovider -q` -> "............ [100%]".

Filed: none.

Gates: `uv run frob check --ticket T-0960` chunked loop (lint/static/
gates-fast/gates-native/gates-security) all pass with 0 errors after
re-running `frob ticket sweep T-0960` post scope-widen (PRE001 cleared).
Remaining warnings across all stages are pre-existing repo-wide debt, not
introduced by this ticket.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_process_bounds.py::TestMissingInterfaceClassification::test_kernel_interface_node_without_classification_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_process_bounds.py::TestMissingInterfaceClassification::test_discharged_and_non_kernel_interface_nodes_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_process_bounds.py::TestMissingInterfaceClassification::test_waiver_discharges_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_process_bounds.py::TestUnprovenInterfaceClassification::test_declared_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_process_bounds.py::TestUnprovenInterfaceClassification::test_declared_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_process_bounds.py::TestUnprovenInterfaceClassification::test_declared_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_process_bounds.py::TestMissingProcessBounds::test_deployed_process_node_without_bounds_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_process_bounds.py::TestMissingProcessBounds::test_discharged_and_non_deployed_process_nodes_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_process_bounds.py::TestMissingProcessBounds::test_waiver_discharges_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_process_bounds.py::TestUnprovenProcessBounds::test_declared_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_process_bounds.py::TestUnprovenProcessBounds::test_declared_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_process_bounds.py::TestUnprovenProcessBounds::test_declared_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 0 error(s), 4999 warning(s), 220 waived
- error-findings: none (measured, zero errors)
