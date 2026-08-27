---
id: T-3119
title: frob refactor verbs' Verify phase never checks import breakage outside the
  plan's own touched files
state: in-progress
kind: bug
origin: agent
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/_commit.py
- src/frob/refactor/_verify.py
- src/frob/refactor/_split.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/refactor/_split.py
  reason: 'ticket''s own Description+Plan explicitly names run_split''s Verify phase
    as a target; discovered _split.py''s _run_chunk_verify duplicates _commit.py::run_verify_outcomes
    instead of calling it, so the T-3119 fix in _commit.py/_verify.py alone never
    reaches the split verb -- proven live: reverting T-3122''s fix and running the
    strengthened corpus still showed chunk success=True with T-3119''s fix already
    committed, because run_split never calls the code path that fix lives in'
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27 while building T-3110's corpus. `run_split`/
`run_move_module`/`run_refactor`'s own `verify_import_resolution` step
only checks the plan's own `touched_files` list -- it never re-scans the
WHOLE repo tree for import breakage a rewrite could have caused outside
that list (a caller elsewhere the scan itself never touched, or a
downstream consumer of a re-export chain).

The corpus's `_assert_all_py_files_parse` helper (test-only, added in
T-3110) proves the concept: it walks every `.py` file under the fixture
root and `ast.parse`s it, catching anything the plan's own touched-set
check would miss. Add an unconditional whole-tree post-apply import
check (at minimum an `ast.parse` sweep, ideally the same local-module
resolution `verify_import_resolution` already does for local imports)
to `run_split`/`run_move_module`/`run_refactor`'s own Verify phase,
gating `success` the same way `import_resolution` already does.

This is exactly the class of defect T-3105 shipped: `success=True` on a
repo that could not `import frob.gates._models`, because the corruption
was outside anything `verify_import_resolution`'s touched-files scope
covered at the time.

Filed instead of fixed directly because T-3110's own declared scope is
`tests/test_refactor_corpus.py` only -- a production-code change to the
refactor engine's Verify phase is a separate unit of work.
