---
id: T-4358
title: Reconcile ruff-check/ty parsers' treatment of a tool absent from the target
  project
state: done
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/parsers/ruff.py
- src/frob/process/parsers/ty.py
- tests/unit/test_tool_absent_parser_reconcile.py
- tickets/T-4359/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_tool_absent_parser_reconcile.py
  reason: 'T-4358: test coverage for the parser fix, plus the follow-up ticket filed
    for out-of-scope caller wiring'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tickets/T-4359/**
  reason: 'T-4358: test coverage for the parser fix, plus the follow-up ticket filed
    for out-of-scope caller wiring'
  actor: logan
  at: '2026-09-08'
evidence:
- tests/unit/test_tool_absent_parser_reconcile.py::TestRuffAbsentToolIsUnmeasured::test_spawn_failure_is_unmeasured_not_error
- tests/unit/test_tool_absent_parser_reconcile.py::TestRuffEmptyOutputWithoutStderrEvidenceStaysAnError::test_no_stderr_argument_is_still_an_error
- tests/unit/test_tool_absent_parser_reconcile.py::TestRuffPresentButBrokenStaysAnError::test_truncated_json_is_still_malformed_even_with_stderr_set
- tests/unit/test_tool_absent_parser_reconcile.py::TestTyAbsentToolIsUnmeasured::test_spawn_failure_text_is_unmeasured
- tests/unit/test_tool_absent_parser_reconcile.py::TestBothParsersAgree::test_ruff_and_ty_both_report_zero_errors_on_absent_tool
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-4354.

T-4354 decided and documented (docs/modules/process.md, "Tool absent from
the target project") that a target project's own environment lacking
ruff/ty is a legitimate, not-installed state that must be reported as
UNMEASURED everywhere, never a hard ERROR -- matching the doctrine
project_import_argv already established for the importing spawn kind.
It added frob.process._project_tool.tool_absent_from_project(tool,
exit_code, stderr) as the one shared classifier for uv run's own
"could not spawn the tool" shape (exit 2, "Failed to spawn: `<tool>`"),
and wired it into resolve_project_tool (Err(ProjectToolError.ToolAbsent)).

T-4354's scope was src/frob/process/_project_tool.py only, so the actual
parsers were left inconsistent:

- src/frob/process/parsers/common.py's tool_no_output_result (T-4308)
  is what ruff-check's parser calls for this shape today, producing a
  hard ERROR diagnostic ("ruff produced no output -- the tool did not
  run").
- ty's parser instead falls through its diagnostic regexes into
  T-4309's silent-nonzero-exit UNMEASURED routing for the same shape.

Fix: have both parsers call tool_absent_from_project on the raw
exit_code/stderr before falling back to their current heuristics, and
when it is True, report UNMEASURED (not_measured / an info-severity
diagnostic per T-2391's doctrine) consistently -- removing ruff-check's
ERROR path for this specific shape rather than adding a matching ERROR
path to ty, per T-4354's documented decision. Update/add tests in
tests/unit covering both parsers' handling of a real "Failed to spawn"
capture, plus a regression test that the 14 T-4352-shaped fixture
failures (a fixture project with no ruff/ty dependency) no longer FAIL
under this classification once ty's/ruff's project_tool_argv-driven
CI/dev invocation lacks a global fallback on PATH.