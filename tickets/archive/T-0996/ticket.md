---
id: T-0996
title: 'two system tests red on main: gitless render-lint severity + scaffold-dx immediate-check'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tests/system/test_cli_check.py
- tests/system/test_scaffold_dx.py
- src/frob/**
- tests/unit/test_check_tool_unavailable.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_check_tool_unavailable.py
  reason: 'Coordinator-directed: TEST016 mutation-evidence gap on _run_ty''s argv

    construction (src/frob/check/_python.py:138/141, binop Div swapped) is

    killable at the unit level even though the system evidence hits it only

    through the separately-installed global frob binary. Add a direct unit

    test on _run_ty''s argv construction to tests/unit/test_check_tool_unavailable.py

    (the existing home for _run_ty''s tool-availability unit tests) instead of

    relying on --skip-mutation-evidence.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
- tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
- tests/unit/test_check_tool_unavailable.py::TestTyHermeticRootResolution::test_extra_search_path_and_python_pin_to_root
- tests/unit/test_check_tool_unavailable.py::TestTyHermeticRootResolution::test_no_src_or_venv_omits_the_pinning_flags
designated_repro_test: null
acceptance:
- text: given current main, when both named tests run in isolation, then both pass
  evidence:
  - tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
  - tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
  - tests/unit/test_check_tool_unavailable.py::TestTyHermeticRootResolution::test_extra_search_path_and_python_pin_to_root
  - tests/unit/test_check_tool_unavailable.py::TestTyHermeticRootResolution::test_no_src_or_venv_omits_the_pinning_flags
threat: null
component: null
---
Surfaced by the coordinator coverage run and confirmed failing IN ISOLATION on current main (no longer the documented order-dependent flake): (1) tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root -- previously passed in isolation per multiple agent reports, so something recent regressed the gitless severity downgrade path or the test env; bisect against the last week of gate severity promotions (SEC110/PII/PERF/ARCH families, DUP003, DOC007) which are the likeliest suspects for a severity-behavior change. (2) tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately -- a freshly scaffolded python tool no longer passes check immediately; likely a newly promoted gate now fires on the scaffold template (the templates must be updated to satisfy whatever new error-tier rule hits them, or the gate must reasonably exempt fresh scaffolds). Fix both properly -- these two tests are the canary for downstream repo scaffolding UX.