---
id: T-3596
title: 'frob refactor move/split: no import carry-forward, no caller-side bare-name
  repoint'
state: queued
kind: feature
origin: agent
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/**
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
Found while working T-3586 (splitting tests/test_gates.py). Two
confirmed gaps in `frob refactor move`, distinct from T-3587:

1. NO IMPORT CARRY-FORWARD FOR MOVE. `split`'s T-3122 fix
   (`needed_import_ops_for_symbols`, called from `_split.py` only)
   copies forward the source module's own top-level imports a moved
   symbol's body/default-args need. `move` (`_transaction.py`/
   `_apply.py`'s `build_move_ops`, used by both `move` and `split`)
   never calls it -- only `_split.py:261` does. Moving a function whose
   default argument reads a module-level import (e.g. `def f(x=
   SomeEnum.A)`) succeeds `import_resolution`/`pytest_collect` (those
   only check import-time correctness) but fails at actual call time
   with a `NameError`, invisible to the verb's own verification.
   Reproduced repeatedly: moving `tests.test_gates._violation` (default
   arg `severity=Severity.WARN`) to `tests.conftest` required manually
   adding `from frob.gates import Severity` to the destination before
   the move's own `module_import` check would pass.

2. NO CALLER-SIDE BARE-NAME REPOINT FOR MOVE/SPLIT. Neither verb
   patches a file that references the moved symbol as a BARE NAME
   (no explicit `from SOURCE import symbol` statement to rewrite) when
   that file is in the SAME module the symbol used to live in -- the
   SOURCE module's own other classes/functions, or (for `split`) the
   newly-created destination module, which never had its own import of
   the symbol to begin with since it was in the same file. Both need a
   `from tests.conftest import symbol` added by hand after the move;
   the verb's own docs describe this as "rewrites every import/call
   site" but the scanner (`scan_references`) apparently only follows
   explicit cross-module import statements, not same-module bare-name
   usage that becomes cross-module after the move.

SUGGESTION: (a) reuse `needed_import_ops_for_symbols` from
`build_move_ops` (both verbs share the same underlying op-builder per
docs/commands/refactor.md's Split verb section) instead of only from
`_split.py`; (b) extend `scan_references` to also find bare-name Name
nodes in the SOURCE module (and, for split, the newly-created DEST
module) that resolve to the moved symbol via the module's own prior
top-level scope, and emit an import-add op for them the same way an
explicit cross-module import gets rewritten today.

Also noted (not filed as a fix target, just documented for T-3586's
follow-ups): a module-level CONSTANT (a plain `Name = ...` assignment,
not a `def`/`class`) cannot be moved by `move`/`split` at all --
`_resolve.py::resolve_symbol`'s own docstring scopes v1 to
function/class defs. This may be intentional v1 scoping rather than a
bug; flagging in case it should join the EPIC backlog.
