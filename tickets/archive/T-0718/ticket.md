---
id: T-0718
title: 'check: project-type detection reports ''unknown'' when a fixture has no pyproject.toml,
  unrelated to git'
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/**
- tests/system/test_cli_check.py
- tests/system/test_cli_perf.py
- src/frob/check/__init__.py
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/check/__init__.py
  reason: 'Ticket body assumed the project-type detector lived under src/frob/app/config.py,
    but

    detect_project_type actually lives in src/frob/check/__init__.py -- verified by
    grep and

    confirmed as the sole call site producing the ''unknown'' CHECK001 result described
    in the

    ticket. Extending scope to cover the real fix location.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/test_check.py
  reason: 'Added a regression unit test for the detect_project_type fix directly alongside
    its

    existing TestDetectProjectType suite in tests/unit/test_check.py -- this file
    was not

    in the original declared scope (only tests/system/test_cli_check.py and

    tests/system/test_cli_perf.py were), extending to cover the actual test file touched.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_check.py::TestDetectProjectType::test_bare_py_file_no_pyproject_is_python
- tests/system/test_cli_check.py::TestCheckTicketScopedAlwaysReportsOnFailure::test_ticket_scoped_nonzero_exit_has_diagnostic_output
- tests/system/test_cli_check.py::TestCheckGatesStage::test_only_gates_passes_once_bound_and_tested
- tests/system/test_cli_perf.py::TestCheckOnlyPerf::test_perf001_fixture_warns_but_check_exits_zero
designated_repro_test: null
threat: null
component: null
---
Found while working T-0705. tests/system/test_cli_check.py::TestCheckTicketScopedAlwaysReportsOnFailure::test_ticket_scoped_nonzero_exit_has_diagnostic_output, tests/system/test_cli_check.py::TestCheckGatesStage::test_only_gates_passes_once_bound_and_tested, and tests/system/test_cli_perf.py::TestCheckOnlyPerf::test_perf001_fixture_warns_but_check_exits_zero all fail with CHECK001 'unknown project type: 'unknown' (no dispatchable language stage)' even though each fixture DOES git init + commit (so this is not the T-0705 git-ls-files mechanism at all). Each of these fixtures writes a bare .py file with no pyproject.toml. Project-type detection (src/frob/app/**, exact site not yet located) appears to require pyproject.toml presence rather than falling back to extension-based detection when only .py files are tracked. Investigate src/frob/app/config.py's project-type resolution and either fix the fixtures (add a pyproject.toml) or fix the detector, whichever is the real contract.