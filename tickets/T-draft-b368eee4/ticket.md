---
id: T-draft-b368eee4
title: SCOPE002 private-helper closure resolves calls by bare short name, not import
  binding
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_debt_deprecated.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3912: importing tests.conftest._write and calling it as _write(...) made ticket scope T-3912's SCOPE002 closure check report a dependency on tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage._write (an unrelated class method with the same bare name), not on the actually-imported tests.conftest._write. Widening scope to satisfy the false positive would have pulled in test_compliance.py's own large unrelated fan-out (37 further scope-closure warnings) purely because of a name collision. Worked around in T-3912 by aliasing the import (from tests.conftest import _write as _write_fixture) to dodge the bare-name match; the underlying private-helper-call resolver should resolve call sites through the actual import binding (module + name), not a repo-wide bare short-name search.