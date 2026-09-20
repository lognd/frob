---
id: T-4642
title: land Tier-A directive canonicalizer emits lines over the ruff limit that the
  land's own ruff gate then refuses (E501), self-refusing every ticket whose frob:doc
  anchor is long
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine.py
- tests/gates_suite/test_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: fix _rewrite_line_substring to noqa-guard a rewrite that pushes a directive
    line over the ruff limit
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/gates_suite/test_fix_engine.py
  reason: 'positive control: a directive that expands past 88 chars survives Tier-A
    and ruff'
  actor: logan
  at: '2026-09-19'
evidence:
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_doc002_rewrite_that_exceeds_ruff_limit_gets_noqa
designated_repro_test: tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_doc002_rewrite_that_exceeds_ruff_limit_gets_noqa
acceptance:
- text: 'A directive rewrite (DOC007 dotted-form / DOC002 fuzzy-slug) that pushes
    a line past the resolved line-length limit gets a trailing noqa: E501 appended
    in the same write, and the rewritten file is clean under a real ruff check.'
  evidence:
  - tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_doc002_rewrite_that_exceeds_ruff_limit_gets_noqa
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
