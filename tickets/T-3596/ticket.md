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
body_changes:
- mode: append
  reason: append T-3628's discovered tool gaps (module-level variable dependency not
    carried; decorator dropped + self-import bug on split)
  actor: logan
  at: '2026-09-01'
  old_length: 2778
  new_length: 6426
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


Found while working T-3628 (splitting src/frob/process/_lock.py).
Two MORE confirmed gaps, distinct from the import-carry-forward gaps
above (repro'd against this exact checkout, commit fbe638113 base):

3. MODULE-LEVEL VARIABLE (not import) dependency is neither moved nor
   re-imported. `_lock.py`'s `_msvcrt_acquire_blocking`/`_msvcrt_release`
   read the module-level `msvcrt: ModuleType | None` global (populated by
   a top-level try/except ImportError). `frob refactor split
   frob.process._lock --symbols _msvcrt_acquire_blocking,_msvcrt_release
   --into frob.process._lock_msvcrt` reported success=True (import_
   resolution PASS, module_import PASS) but the moved functions' own
   body still bare-references `msvcrt`/`fcntl`, now undefined in the new
   module -- `NameError: name 'msvcrt' is not defined` at actual call
   time (`tests/unit/test_process_lock.py::TestPortableFlock::test_
   windows_branch_selected_when_fcntl_absent` and 3 other windows-branch
   tests, all passing on the ORIGINAL unsplit file). Same failure class
   as gap 1 above (verification only checks import-time, not call-time,
   correctness) but for a plain `Name = value` / try-except-populated
   module global, not an `import` statement -- `needed_import_ops_for_
   symbols` presumably only walks `Import`/`ImportFrom` nodes, not every
   free variable a moved body references.

4. `split` DROPS a moved function's OWN DECORATOR and inserts a
   SELF-IMPORT into the destination module. Splitting the larger
   `derived_state_lock` (`@contextmanager`-decorated, ~140 lines,
   `--symbols derived_state_lock --into frob.process._derived_lock
   --chunk-size 1`) reported success=True, but the resulting
   `_derived_lock.py`: (a) the moved `def derived_state_lock(...)` lost
   its `@contextmanager` decorator entirely (present immediately above
   it in the source); (b) the tool inserted `from frob.process._
   derived_lock import (...)` -- importing from ITS OWN destination
   module, a no-op/self-reference, rather than importing the still-
   undefined `_process_registry_lock`/`_process_held_counts` module
   globals from `frob.process._lock` (source) that the moved function's
   OWN BODY (and `held_registry_keys`, moved in an earlier successful
   chunk) needs -- gap 3's variable-dependency issue compounding here
   since two DIFFERENT chunks both reference the same un-carried
   globals. The decorator loss alone breaks EVERY caller (`derived_
   state_lock(root, exclusive=True)` returns a bare generator, not a
   context manager -- `'generator' object does not support the context
   manager protocol` crashed `frob check` itself, repo-wide, the instant
   this land-adjacent `--only arch` check tried to import the module).
   Reproduced twice (retried after a clean rollback, identical result
   both times) -- not a one-off race.

Both gaps made `frob refactor split`'s own reported `success=True` /
`[PASS] import_resolution` / `[PASS] module_import` verification
UNRELIABLE for any symbol whose body reads a module-level free variable
its own file didn't `import` (gap 3), and unreliable for decorator
preservation on a larger multi-hundred-line function (gap 4) -- both
confirmed by full rollback to the pre-split commit and re-running
`tests/unit/test_process_lock.py` clean (30/30 passing) immediately
before each attempt, then re-running it again post-split to surface the
failure the tool's own verification missed.

T-3628 could not complete its ARCH102 split using this tool as a
result -- filed here per that ticket's own "append tool gaps to T-3596"
instruction rather than working around the bug with a hand-copy.
