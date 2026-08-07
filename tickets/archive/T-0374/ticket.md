---
id: T-0374
title: extract shared _collect_file_hashes/_walk/_sha_of helper (gates._coverage vs
  gates._baseline)
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0187
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
- src/frob/gates/_baseline.py
- src/frob/gates/_filehash.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestBaselineDelta::test_stamp_and_load_round_trip
- tests/test_gates.py::TestBaselineDelta::test_baseline_not_stale_when_files_unchanged
- tests/test_gates.py::TestBaselineDelta::test_baseline_stale_when_file_changes
- tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_roundtrip
- tests/test_gates.py::TestCoverageLoad::test_joins_via_repo_relative_source
- tests/test_gates.py::TestCoverageLoad::test_multi_source_picks_the_root_that_joins
- tests/test_gates.py::TestCoverageLoad::test_missing_coverage_xml
designated_repro_test: null
threat: null
component: null
---
T-0364 dup triage: gates/_coverage.py::_collect_file_hashes and gates/_baseline.py::_collect_file_hashes are byte-identical (same _walk/_SOURCE_EXTS/_sha_of pattern too), currently justified in _baseline.py's docstring as 'independent artifacts with the same staleness shape, not a shared abstraction worth forcing together.' That reasoning covers the CONCEPT staying separate, not the literal duplicated 15-line file-walk+hash body -- a real extraction candidate: one frob.gates._filehash (or similar) module exporting _walk/_sha_of/_collect_file_hashes, imported by both _coverage.py and _baseline.py, with each stamp keeping its own TTL/threshold logic layered on top. Filed under T-0187 rather than done inline because gates/__init__.py is a wide, high-traffic module and this needs a careful look at both stamps' call sites before moving shared code. Parent: T-0187.