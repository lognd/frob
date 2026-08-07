---
id: T-1161
title: 'doctor/testing: detect root-venv entrypoint shebangs pointing outside this
  venv; collector must fail loudly, not emit 6219 COV003s'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- src/frob/doctor.py
- tests/test_testing_collect.py
- src/frob/gates/__init__.py
- docs/guides/install.md
- docs/modules/testing.md
- docs/modules/gates.md
- tests/system/test_cli_doctor.py
- tests/test_gates.py
- frob.lock
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: coverage gate (COV003 per-evidence flood -> ONE error) lives in gates/__init__.py,
    same shape T-1148 needed for NATIVE001; the declared scope only covered the collector
    side
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/guides/install.md
  reason: frob:doc anchors for doctor.py / testing/_models.py / gates/__init__.py
    public symbols this ticket touches
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/testing.md
  reason: frob:doc anchors for doctor.py / testing/_models.py / gates/__init__.py
    public symbols this ticket touches
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/gates.md
  reason: frob:doc anchors for doctor.py / testing/_models.py / gates/__init__.py
    public symbols this ticket touches
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/system/test_cli_doctor.py
  reason: doctor venv-shim scan (part a) unit-testable coverage; frob:tests directives
    on scan_venv_shims/VenvShimDrift point here per existing doctor test-suite convention
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_gates.py
  reason: coverage_gate/_load_tests python_collection_failed wiring regression tests
  actor: logan
  at: '2026-07-28'
- op: add
  glob: frob.lock
  reason: frob ack src/frob/doctor.py::run_diagnosis and gates/__init__.py::coverage_gate
    writes derived DRIFT001 ack digests here
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001/SYS104: new public symbols (VenvShimDrift, scan_venv_shims,
    python_collection_failure_detail, new test classes) need interface= attrs synced
    via frob sys sync-interface'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_testing_collect.py::TestPythonCollectionFailureDetail::test_none_before_any_call
- tests/test_testing_collect.py::TestPythonCollectionFailureDetail::test_outer_collection_failure_records_detail_with_stderr_tail
- tests/test_testing_collect.py::TestPythonCollectionFailureDetail::test_successful_collection_clears_a_prior_failure_detail
- tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_flags_shebang_outside_venv
- tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_clean_shebang_reports_nothing
- tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_no_venv_directory_reports_nothing
- tests/test_gates.py::TestCoverageGate::test_load_tests_captures_python_collection_failure_detail
- tests/test_gates.py::TestCoverageGate::test_coverage_gate_reports_one_violation_on_python_collection_failure
designated_repro_test: null
acceptance:
- text: GIVEN .venv/bin entrypoint scripts whose shebang points outside this venv
    (e.g. a removed worktree's python) WHEN frob doctor runs THEN it reports each
    corrupted shim with the uv sync --reinstall-package repair command
  evidence:
  - tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_flags_shebang_outside_venv
- text: GIVEN pytest --collect-only exits nonzero WHEN the coverage gate needs collection
    THEN it emits ONE error naming the collection failure and its stderr tail instead
    of an unresolved-evidence COV003 for every archived ticket
  evidence:
  - tests/test_gates.py::TestCoverageGate::test_coverage_gate_reports_one_violation_on_python_collection_failure
threat: null
component: null
---
2026-07-28 incident: worktree uv operations rewrote the ROOT venv's pytest shim shebang to point at .claude/worktrees/w18-tickets/.venv/bin/python; after that worktree was removed, uv run pytest broke, collect_python_tests returned CollectFailed, and the coverage gate emitted 6219 COV003 errors (one per archived evidence id) with a misleading refresh-the-cache hint. Two misattribution layers: (1) doctor has no venv-shim integrity check; (2) the coverage gate degrades a total-collection failure into per-evidence noise. Sibling of T-1148 (natives staleness honest-failure); same design: detect the environment fault once, loudly, with the repair command.