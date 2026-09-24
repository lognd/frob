---
id: T-5309
title: 'WEBSEC109-116: code-injection and deserialization sinks'
state: done
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5307
parent: T-5141
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_deser.py
- tests/fixtures/webapp/websec1xx/deser/**
- docs/modules/webapp-websec-deser.md
- tests/unit/test_websec_deser.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/websec1xx/**
  reason: narrow shared fixture glob to a per-leaf subdirectory so the four injection
    leaves can hold concurrent leases
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/fixtures/webapp/websec1xx/deser/**
  reason: narrow shared fixture glob to a per-leaf subdirectory so the four injection
    leaves can hold concurrent leases
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/modules/webapp-websec-deser.md
  reason: family doc, per shared brief
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/test_websec_deser.py
  reason: unit test binding for gate fold
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: null
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/unit/test_websec_deser.py::test_websec_deser_findings_no_framework_short_circuits
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc109_positive-WEBSEC109-True]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc109_negative-WEBSEC109-False]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc110_positive-WEBSEC110-True]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc110_negative-WEBSEC110-False]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc111_positive-WEBSEC111-True]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc111_negative-WEBSEC111-False]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc112_positive-WEBSEC112-True]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc112_negative-WEBSEC112-False]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc113_positive-WEBSEC113-True]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc113_negative-WEBSEC113-False]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc114_positive-WEBSEC114-True]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc114_negative-WEBSEC114-False]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc115_positive-WEBSEC115-True]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc115_negative-WEBSEC115-False]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc116_positive-WEBSEC116-True]
- tests/unit/test_websec_deser.py::test_websec_deser_findings_fixture[webesc116_negative-WEBSEC116-False]
- tests/unit/test_websec_deser.py::TestWebsecFindingsGateHook::test_websec_findings_emits_violation
- tests/unit/test_websec_deser.py::TestWebsecFindingsGateHook::test_websec_findings_short_circuits_on_empty_frameworks
- tests/unit/test_websec_deser.py::TestTaintGateDiscoversWebsecDeser::test_taint_gate_reports_planted_webesc110_fixture
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5309
branch: t-5309
---
SSTI (render_template_string/Template(userInput)), eval/exec/new Function, yaml.load without SafeLoader, pickle.load(s) on untrusted data, subprocess shell=True/os.system with interpolated input, LDAP filter string concatenation, NoSQL/Mongo operator-key injection (unsanitized $where/$gt/$ne from request JSON), LaTeX --shell-escape. Python AST (SEC005 substrate reuse) for most; LaTeX is a build-step regex scan of the compile invocation. Fixture per rule id.