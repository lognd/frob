---
id: T-4809
title: 'Style conformance sweep across the python-family templates: bugbear, license
  notice, future annotations, compat shim, stubs and src layout'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4768
- T-4769
parent: T-4757
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/bases/python/**
- tests/unit/test_scaffold_style_conformance.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: Given every rendered python-family module, when its first statement is read,
    then it is the future-annotations import
  evidence: []
- text: Given the rendered ruff selection, when it is read, then it contains B
  evidence: []
- text: Given the rendered project metadata, when the license is read, then it is
    the GPL v3 short notice refs/python.md mandates
  evidence: []
- text: Given every rendered python-family module, when its imports are read, then
    none imports the stdlib TOML reader directly, and a compatibility shim module
    is rendered
  evidence: []
- text: Given the conformance test, when it is run against the pre-fix templates,
    then it fails, and the failure count is recorded in the done report
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The style conformance findings the audit turned up that do not belong to any
other leaf. One sweep, because each is a one-line template edit and filing
seven tickets for seven lines would cost more than the work.

1. src layout for pybind11 (package at the repository root today) and pyo3
   (a non-standard python directory today), per refs/python.md. Coordinate
   with the cpp and rust base leaves, which also touch those manifests.
2. Add the bugbear rule set to the ruff selection: the python pyproject
   template selects four rule families and omits B.
3. License: the template sets a permissive license text while refs/python.md
   mandates the GPL v3 short notice.
4. A future-annotations import as the first line of EVERY generated module.
   Today it is present in the config and logging templates and absent from
   the entry point, the App module and both package initialisers.
5. A compatibility shim module, rather than importing the stdlib TOML reader
   directly in two generated modules. The direct import is masked today only
   by a Python floor of 3.11, which itself contradicts refs/python.md's 3.10
   target -- decide and record which floor the scaffold targets.
6. A stubs directory, per refs/python.md, which no type renders.

Positive control: a conformance test that renders every python-family type
and asserts, per rendered module, that the future-annotations import is the
first statement; that the ruff selection contains B; that the license string
is the mandated one; and that no generated module imports the stdlib TOML
reader directly. The test must fail on today's templates before the fix --
record the failure count in the done report.
