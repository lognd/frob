---
id: T-1144
title: 'arch: check/ + process/parsers ToolResult-builder abstraction-opportunity
  residue (T-1124 remainder)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/**
- src/frob/process/parsers/**
- docs/modules/arch.md
- src/frob/arch/_python.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_python.py
  reason: 'Investigation confirmed all 4 ToolResult/ToolResult|None-returning

    groups (24 members total across check/_native.py, check/_python.py,

    check/_ts.py, check/__init__.py, app/check_runner.py,

    process/parsers/common.py, process/parsers/junit.py, and the arch/

    cycle/dup CLI runners) are frob''s own check-stage-runner return-type

    convention, not accidental duplication -- ToolResult is the domain type

    every individual check-stage/tool-result builder returns by

    construction, the same class of finding T-1141 just generalized

    `_is_check_registry_family`''s sibling exclusion for

    (`_is_gate_rule_builder_family`, Violation). The actual body-level

    duplication already found (T-1124''s `_opt_in_deploy_stage_result`,

    `_missing_tool_result` forwarding to `tool_unavailable_result`) is

    already extracted; what remains is purely the shared-return-type

    false-positive class, whose fix lives beside T-1141''s own exclusion in

    the arch detector (src/frob/arch/_python.py), outside T-1144''s

    originally-declared scope. Adding it so the mirrored exclusion can

    land in the same place as its precedent.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/test_arch.py
  reason: 'The new arch/_python.py exclusion (this ticket) needs a unit test, and

    the closure warning already flagged tests/unit/test_arch.py as covering

    src/frob/arch/_python.py::PythonAdapter -- adding it so the new test can

    land alongside the exclusion it verifies.

    '
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/test_arch.py::TestToolResultBuilderExclusion::test_toolresult_returning_group_not_flagged
- tests/unit/test_arch.py::TestToolResultBuilderExclusion::test_non_toolresult_returning_group_still_flagged
- tests/unit/test_arch.py::TestToolResultBuilderExclusion::test_return_type_membership_matches_both_shapes
designated_repro_test: null
threat: null
component: null
---
T-1124 found two abstraction-opportunity groups that keep firing from
`frob check --only arch` because the shared signature carries a specific
domain type (`ToolResult`), and cannot be resolved within
`src/frob/app/**` scope:

1. `(Path) -> ToolResult | None` group (7 members): `check_runner.py`'s
   `_deploy_drift_result`/`_deploy_conformance_result` (already
   consolidated into a shared `_opt_in_deploy_stage_result` helper by
   T-1124) plus `src/frob/check/__init__.py::_derived_state_integrity_result`,
   `src/frob/check/_native.py::_run_clang_format`/`_run_cargo_fmt_check`/
   `_run_cargo_valgrind`, `src/frob/check/_python.py::_run_bind`.
2. `(str, str) -> ToolResult` group (5 members): `check_runner.py`'s
   `_skip_note_result` plus `src/frob/check/_ts.py::_missing_tool_result`,
   `src/frob/process/parsers/common.py::tool_unavailable_result`/
   `tool_disabled_result`, `src/frob/process/parsers/junit.py::parse_junit_xml`.

Investigate whether these 5 check/-stage "build a ToolResult for an
opt-in/skip/missing-tool condition" functions genuinely share extractable
logic across `src/frob/check/**` and `src/frob/process/parsers/**`, or
whether this is a coincidental signature collision that the arch
detector's specificity heuristic (docs/modules/arch.md) should learn to
exclude. Scope: src/frob/check/**, src/frob/process/parsers/**,
docs/modules/arch.md (if the detector itself needs an exclusion) or the
consuming files (if a real shared helper is extractable).