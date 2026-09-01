---
id: T-3658
title: restore pathlib import line pruned from PY_SAMPLE fixture literal
state: in-progress
kind: bug
origin: human
created: '2026-09-01'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
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
Run 33521416410, ubuntu AND macOS (reproduced locally):
  tests/unit/test_outline.py::test_py_outline_imports
  E  AssertionError: assert 'pathlib' in ['os']

ROOT CAUSE (measured): T-3595's land commit 2b188e958 contains this hunk
in tests/conftest.py:

  @@ -1558,7 +1558,6 @@
   PY_SAMPLE = b"""\
   import os
  -from pathlib import Path

The refactor tooling's import-consolidation/pruning pass removed an
import line that lives INSIDE a bytes string literal (the outline
fixture's SAMPLE SOURCE, not a real import). Fix here: restore the
`from pathlib import Path` line inside PY_SAMPLE at tests/conftest.py
(~line 1560). Verify: tests/unit/test_outline.py passes; grep the same
land diff for any OTHER string-literal lines it pruned (check the full
2b188e958 tests/conftest.py hunks for deletions inside quoted blocks).
The VERB defect itself (lexical prune touching literal content) is
filed separately in the refactor-verbs series -- do not fix tooling
here. Scope: tests/conftest.py.

Checked: `git show 2b188e958 -- tests/conftest.py` has exactly ONE hunk
touching PY_SAMPLE's contents (the pathlib line above); the rest of
that commit's tests/conftest.py diff is pure addition (new helper
functions appended at the end of the file), so no other string-literal
line was pruned by this land.
