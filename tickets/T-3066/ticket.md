---
id: T-3066
title: frob refactor split/move-module false-refuses on any nested import of the source
  module
state: queued
kind: bug
origin: human
created: '2026-08-26'
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
`frob refactor split` (and by extension anything sharing
`src/frob/refactor/_scan.py`'s import-resolution scan, e.g. `move-module`)
refuses to move ANY symbol out of a module the moment that module has a
single nested (function-local, or inside an `if`/`try` block) `from`
import ANYWHERE in the repo -- even one importing a completely different,
unrelated symbol from the same module that is not part of the move.

ROOT CAUSE: `_shares_line_with_sibling_statement()` in
`src/frob/refactor/_scan.py:57` calls `ast.walk(tree)` to look for a
"sibling" statement occupying the same physical line as the `ImportFrom`
node. `ast.walk` yields EVERY statement in the tree, including every
ancestor compound statement (the enclosing `FunctionDef`, `If`, `Try`,
...) that contains `node`. An enclosing `FunctionDef`'s own line span
always overlaps its body's import statement's line span, so the overlap
check at line 73 (`other.lineno <= end and node.lineno <= other_end`)
returns True for the import's OWN ENCLOSING SCOPE, not a genuine
semicolon-joined sibling. Every function-local or block-nested `from X
import Y` is therefore misclassified as "shares its physical line with
another statement (semicolon-joined)" and refused, regardless of whether
any such sibling statement actually exists.

REPRODUCED 2026-08-27 on `frob refactor split frob.gates._models
--symbols Severity,WaiverRef,DebtEntry,Violation --into
frob.gates._findings` (T-3064): it failed at the `import_resolution`
verify stage with ~40 false "unresolved: ... shares its physical line
with another statement (semicolon-joined)" findings for files that import
OTHER, non-moved names from the same source module (`GateError`,
`GateReport`, `GateStats`) via a function-local or `if TYPE_CHECKING:`
import -- e.g. `src/frob/gates/decisions.py:109` (a plain function-local
`from frob.gates._models import Severity, Violation` with no sibling
statement on that line at all) and `src/frob/gates/_coverage_sites.py:81`
(a `TYPE_CHECKING`-guarded import). `cat -A` on the flagged lines confirms
no semicolon and no second statement present -- the block/function
enclosing the import is what "shares the line".

Two separate defects worth fixing together:
  1. The scan should only inspect DIRECT children of `tree.body` (or of
     the relevant enclosing block) for a true sibling, not every node
     `ast.walk` yields.
  2. The scan currently matches ANY `ImportFrom` whose `.module` equals
     the source module, regardless of which names are imported -- an
     import of an untouched symbol should never gate a move of a
     different symbol in the same module. Filtering to imports that
     actually reference one of the moved symbols would shrink the blast
     radius even if defect 1 were not present.

Until fixed, `frob refactor split`/`move-module` is unusable on any module
that has even one nested import anywhere in the repo (common) -- forcing
a fallback to hand-edited imports on exactly the kind of refactor the
verb exists for.

Scope is the detection helper and its caller; a fixture with a genuine
function-local import (no sibling) plus a genuine semicolon-joined import
(real positive) should both be covered.
