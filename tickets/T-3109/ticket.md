---
id: T-3109
title: 'refactor split/move: import-rewrite drops indentation on a nested (function-local/block)
  import'
state: in-progress
kind: bug
origin: human
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
- src/frob/refactor/_scan.py
- tests/test_refactor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_refactor.py
  reason: regression tests for the indentation-loss repro live here alongside the
    existing scan_references test suite
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 6030e2648def4f42985141554f0eb6c7d0a51bef
---
`frob refactor split` (and any `frob refactor move`) corrupts a call site
whose `from <module> import <name>` line is indented -- a function-local
import, or one nested inside an `if`/`try` block. The replacement text
`_rebuild_from_import` builds (and the whole-line `_import_op` writes) has
NO leading whitespace, so replacing an indented import line's exact
`[lineno, end_lineno]` span with an unindented statement leaves the
following, still-indented sibling line orphaned at the wrong indent depth
-- Python then fails to parse the file with "unexpected indent".

REPRO (from a clean worktree on main, AFTER T-3105 lands):

    frob refactor split frob.gates._models \
      --symbols Severity,WaiverRef,DebtEntry,Violation \
      --into frob.findings

This chunk's own Verify phase correctly catches the corruption
(`import_resolution` fails with `unexpected indent`) and the split rolls
itself back cleanly (`rolled_back=True`) -- no damage reaches a commit.
But `success=False`, so the split still cannot complete this extraction.

Confirmed by direct reproduction of the scan+apply against a clean tree
(without going through run_split's auto-rollback): every one of the four
corrupted files (`src/frob/tickets/_land.py:3705`, `tests/test_arch_gate.py`
:146/:250, `tests/test_vet.py`:5237/5470/5500/6497,
`tests/unit/security/test_redact.py:98`) has this exact shape -- a
4-space-indented `from frob.gates._models import Severity` function-local
import, replaced by `scan_references`'s op with the unindented string
`from frob.findings import Severity`.

ROOT CAUSE: `src/frob/refactor/_scan.py::_rebuild_from_import` returns a
bare `from <module> import <names>` string with no leading whitespace, and
`_import_op` writes it verbatim over the node's `[lineno, end_lineno]`
span. Neither function reads or preserves the original statement's
column offset (`node.col_offset`). Fix should prefix the replacement text
with the original line's leading whitespace (or `" " * node.col_offset`)
before building the `RewriteOp`.

This is a THIRD distinct defect found in `frob refactor split`'s
call-site rewrite path by real multi-symbol splits against a
heavily-imported module (after T-3066's semicolon-joined false-refusal
and T-3105's mixed-name over-repoint). All three were found only by
actually attempting the `gates._models` extraction end to end -- confirms
this verb had never been exercised against a real, heavily-imported
module before this drive.

BLOCKS: the T-3086 `gates._models` -> universal-value-types extraction
(retried a third time here). Worktree reset clean (no committed damage);
retry once this is fixed.
