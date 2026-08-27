---
id: T-draft-ac6a1b2d
title: 'refactor split: import-rewrite drags unmoved names to destination module'
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/_scan.py
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
`frob refactor split` corrupts call sites where the source module's `from`
import line mixes a moved symbol with an untouched one -- it repoints the
WHOLE import statement (every name on that line) at the destination module,
not just the moved name.

REPRO (from a clean worktree on main):

    frob refactor split frob.gates._models \
      --symbols Severity,WaiverRef,DebtEntry,Violation \
      --into frob.findings

This completes with `success=True` and commits (T-3066's ast.walk fix
cleared the prior false refusal, so the verb runs end to end now). But the
result leaves the tree import-broken:

    $ python -c "import frob.gates._models"
    ...
    File "src/frob/gates/_baseline.py", line 29, in <module>
        from frob.findings import GateError, Violation
    ImportError: cannot import name 'GateError' from 'frob.findings'

`GateError` was never in `--symbols` -- only `Violation` was moved. Roughly
130 files across `src/` and `tests/` got their import line rewritten the
same way, most incorrectly (any file whose import line named a moved symbol
ALONGSIDE an unmoved one, e.g. `from frob.gates._models import GateReport,
Violation`, ends up entirely repointed at `frob.findings`, which does not
define `GateReport`).

ROOT CAUSE: `src/frob/refactor/_scan.py::_rebuild_from_import` (called from
`scan_references` via `_handle_from_import`).

    def _rebuild_from_import(
        node: ast.ImportFrom, old_ref: SymbolRef, destination: SymbolRef, dest_leaf: str
    ) -> str:
        others = [a for a in node.names if a.name != old_ref.qualname]
        parts = [f"{a.name} as {a.asname}" if a.asname else a.name for a in others]
        parts.append(dest_leaf)
        joined = ", ".join(parts)
        return f"from {destination.module} import {joined}"

`others` is every OTHER name already on that import line -- and the
returned statement points ALL of them (plus the moved name) at
`destination.module`. It should instead leave `others` importing from
`old_ref.module` (a still-valid import, since the source module keeps
those symbols and the split's own re-export shim already covers the moved
one for anyone who didn't need an edit at all) and only add the moved
name's import from the destination. In practice this means the correct
fix is almost always to NOT rewrite call sites in this shape at all --
split's own re-export shim (`build_reexport_shim_op` in `_split.py`)
already makes the source module keep re-exporting every moved name, so
call sites should not need editing merely because ONE name they import
also moved.

This is the same class of defect the ticket that filed T-3066 was
guarding against (a mechanical import rewrite silently corrupting
unrelated code on the same statement) -- T-3066 fixed the sibling-
statement/semicolon case; this is the sibling-NAME-on-the-same-import-
statement case, still unfixed.

BLOCKS: the T-3086 redo of the `gates._models` -> universal-value-types
extraction. That ticket's worktree was reset clean (no committed damage)
once this was found; it should be retried once this is fixed.
