---
id: T-1340
title: 'SUPPRESS001 detector: suppression-dialect registry + evidence-driven mismatch
  detection'
state: done
kind: feature
origin: human
created: '2026-07-31'
priority: high
parent: T-1339
tier: ticket
sprint: null
scope:
- src/frob/gates/_suppress.py
- src/frob/gates/__init__.py
- tests/test_gates_suppress.py
- docs/modules/gates.md
- pyproject.toml
- uv.lock
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: pyproject.toml
  reason: T-1339 ticket description mandates mypy dev dependency + lockfile update;
    original ticket scope included these two files
  actor: logan
  at: '2026-07-31'
- op: add
  glob: uv.lock
  reason: T-1339 ticket description mandates mypy dev dependency + lockfile update;
    original ticket scope included these two files
  actor: logan
  at: '2026-07-31'
- op: add
  glob: design/frob.strata
  reason: frob sys sync-interface mechanically declares the new gates.SuppressionDialect/suppress001_gate/suppression_dialects
    + testsuite.Test* symbols this ticket adds; keeping it in scope avoids a SCOPE001/COV002
    gap
  actor: logan
  at: '2026-07-31'
evidence:
- tests/test_gates_suppress.py::TestSuppressionDialects::test_registers_ty_mypy_ruff
- tests/test_gates_suppress.py::TestSuppressionDialects::test_available_reflects_path_not_project_config
- tests/test_gates_suppress.py::TestLineSuppressions::test_bare_ty_ignore_covers_everything
- tests/test_gates_suppress.py::TestLineSuppressions::test_coded_mypy_ignore_extracts_code_set
- tests/test_gates_suppress.py::TestLineSuppressions::test_both_dialects_on_one_line
- tests/test_gates_suppress.py::TestLineSuppressions::test_no_suppression_present
- tests/test_gates_suppress.py::TestRelativize::test_absolute_path_under_root
- tests/test_gates_suppress.py::TestRelativize::test_already_relative_path_passes_through
- tests/test_gates_suppress.py::TestRelativize::test_path_outside_root_is_none
- tests/test_gates_suppress.py::TestRelativize::test_none_file_is_none
- tests/test_gates_suppress.py::TestSuppress001Gate::test_mypy_suppressed_ty_unsuppressed_fires
- tests/test_gates_suppress.py::TestSuppress001Gate::test_ty_suppressed_mypy_unsuppressed_fires
- tests/test_gates_suppress.py::TestSuppress001Gate::test_both_dialects_present_reports_nothing
- tests/test_gates_suppress.py::TestSuppress001Gate::test_no_suppression_no_finding
- tests/test_gates_suppress.py::TestSuppress001Gate::test_no_available_oracle_reports_nothing
designated_repro_test: null
acceptance:
- text: given a python line carrying a mypy type:ignore and an unsuppressed ty diagnostic
    on the same line, when the suppress gate runs, then SUPPRESS001 reports it naming
    both dialects and the reporting checker's rule code
  evidence:
  - tests/test_gates_suppress.py::TestSuppressionDialects::test_registers_ty_mypy_ruff
  - tests/test_gates_suppress.py::TestSuppressionDialects::test_available_reflects_path_not_project_config
  - tests/test_gates_suppress.py::TestLineSuppressions::test_bare_ty_ignore_covers_everything
  - tests/test_gates_suppress.py::TestLineSuppressions::test_coded_mypy_ignore_extracts_code_set
  - tests/test_gates_suppress.py::TestLineSuppressions::test_both_dialects_on_one_line
  - tests/test_gates_suppress.py::TestLineSuppressions::test_no_suppression_present
  - tests/test_gates_suppress.py::TestRelativize::test_absolute_path_under_root
  - tests/test_gates_suppress.py::TestRelativize::test_already_relative_path_passes_through
  - tests/test_gates_suppress.py::TestRelativize::test_path_outside_root_is_none
  - tests/test_gates_suppress.py::TestRelativize::test_none_file_is_none
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_mypy_suppressed_ty_unsuppressed_fires
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_ty_suppressed_mypy_unsuppressed_fires
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_both_dialects_present_reports_nothing
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_no_suppression_no_finding
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_no_available_oracle_reports_nothing
- text: given a line already carrying both dialects, when the suppress gate runs,
    then it reports nothing
  evidence:
  - tests/test_gates_suppress.py::TestSuppressionDialects::test_registers_ty_mypy_ruff
  - tests/test_gates_suppress.py::TestSuppressionDialects::test_available_reflects_path_not_project_config
  - tests/test_gates_suppress.py::TestLineSuppressions::test_bare_ty_ignore_covers_everything
  - tests/test_gates_suppress.py::TestLineSuppressions::test_coded_mypy_ignore_extracts_code_set
  - tests/test_gates_suppress.py::TestLineSuppressions::test_both_dialects_on_one_line
  - tests/test_gates_suppress.py::TestLineSuppressions::test_no_suppression_present
  - tests/test_gates_suppress.py::TestRelativize::test_absolute_path_under_root
  - tests/test_gates_suppress.py::TestRelativize::test_already_relative_path_passes_through
  - tests/test_gates_suppress.py::TestRelativize::test_path_outside_root_is_none
  - tests/test_gates_suppress.py::TestRelativize::test_none_file_is_none
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_mypy_suppressed_ty_unsuppressed_fires
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_ty_suppressed_mypy_unsuppressed_fires
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_both_dialects_present_reports_nothing
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_no_suppression_no_finding
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_no_available_oracle_reports_nothing
- text: given a suppression for a checker that is not configured in this project,
    when the suppress gate runs, then it reports nothing for that direction
  evidence:
  - tests/test_gates_suppress.py::TestSuppressionDialects::test_registers_ty_mypy_ruff
  - tests/test_gates_suppress.py::TestSuppressionDialects::test_available_reflects_path_not_project_config
  - tests/test_gates_suppress.py::TestLineSuppressions::test_bare_ty_ignore_covers_everything
  - tests/test_gates_suppress.py::TestLineSuppressions::test_coded_mypy_ignore_extracts_code_set
  - tests/test_gates_suppress.py::TestLineSuppressions::test_both_dialects_on_one_line
  - tests/test_gates_suppress.py::TestLineSuppressions::test_no_suppression_present
  - tests/test_gates_suppress.py::TestRelativize::test_absolute_path_under_root
  - tests/test_gates_suppress.py::TestRelativize::test_already_relative_path_passes_through
  - tests/test_gates_suppress.py::TestRelativize::test_path_outside_root_is_none
  - tests/test_gates_suppress.py::TestRelativize::test_none_file_is_none
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_mypy_suppressed_ty_unsuppressed_fires
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_ty_suppressed_mypy_unsuppressed_fires
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_both_dialects_present_reports_nothing
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_no_suppression_no_finding
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_no_available_oracle_reports_nothing
- text: 'reworded [2] (T-1339 DESIGN AMENDMENT, supersedes the original wording above):
    given a dialect with no available diagnostic oracle in this process (a capability
    limit, not ''unconfigured in this project''), when the suppress gate runs, then
    it reports no findings for that direction'
  evidence:
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_no_available_oracle_reports_nothing
threat: null
component: gates
---
Phase 1 of T-1339. Build a SuppressionDialect registry (name, comment syntax, rule-code grammar, how to tell if the tool is configured for this project) with python entries for ty, mypy, and ruff/noqa. Detection is EVIDENCE-DRIVEN: the gate correlates the diagnostics frob check already collects from each configured checker against the suppression comments present on the reporting line. Fire only when line L carries dialect A's suppression AND configured checker B reports an unsuppressed diagnostic at L. No static mypy-code -> ty-code mapping table -- the reporting diagnostic supplies the code.

Direction support must be symmetric (mypy->ty AND ty->mypy), and per T-1339's DESIGN AMENDMENT it is NOT gated on the checker being configured in the consuming project -- the goal is portability, so frob's source must satisfy mypy users even though this repo gates on ty. Add mypy as a dev dependency used purely as a diagnostic ORACLE (never a gate) so the ty->mypy direction has real evidence to correlate against; that is what keeps detection evidence-driven instead of forcing a lossy static code-mapping table.

Supersedes this ticket's third acceptance criterion as originally written ('a checker that is not configured ... reports nothing'). Reinterpret it as: a dialect with no available oracle produces no findings for that direction (a capability limit), NOT a dialect whose tool is merely unconfigured in the consuming project. Re-word the criterion in the same change.

Detection only -- the fix is the sibling ticket.