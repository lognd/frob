---
id: T-3596
title: 'frob refactor move/split: no import carry-forward, no caller-side bare-name
  repoint'
state: in-progress
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
- tests/test_refactor.py
- docs/commands/refactor.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_refactor.py
  reason: regression tests + doc coverage for the T-3596 gap fixes need to be in scope
    for COV/SCOPE gate closure
  actor: logan
  at: '2026-09-01'
- op: add
  glob: docs/commands/refactor.md
  reason: regression tests + doc coverage for the T-3596 gap fixes need to be in scope
    for COV/SCOPE gate closure
  actor: logan
  at: '2026-09-01'
body_changes:
- mode: append
  reason: append T-3628's discovered tool gaps (module-level variable dependency not
    carried; decorator dropped + self-import bug on split)
  actor: logan
  at: '2026-09-01'
  old_length: 2778
  new_length: 6426
- mode: append
  reason: T-3591's split hit four additional documented gap classes beyond T-3586's
    original two
  actor: logan
  at: '2026-09-01'
  old_length: 6426
  new_length: 9532
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


T-3591 found four MORE gap classes in the same move/split verbs (tests/test_ticket_land.py -> tests/ticket_land_suite/ split, 100 classes, 345 tests):

3. MOVE DROPS @pytest.fixture (AND OTHER) DECORATORS. Moving a
   decorated function (frob refactor move tests.mod:v2_repo
   tests.pkg.conftest:v2_repo where v2_repo carried @pytest.fixture)
   silently drops the decorator line -- import_resolution/module_import/
   pytest_collect all report PASS because a bare function with that name
   collects fine; the break only surfaces as a downstream 'fixture not
   found' error in tests that request it as a fixture, in a totally
   different file, minutes later. No verification step actually
   round-trips the AST decorator_list.

4. MOVE CANNOT TOUCH A MODULE-LEVEL CONSTANT AT ALL (v1 scope per
   frob.refactor._resolve.resolve_symbol's own docstring -- known, but
   worth reinforcing with a second incident): _V1_PINNED_CLASSES
   (frozenset) and _STATE_BY_RANK (dict) both needed hand-relocation.
   Worse: when a constant is referenced only by a function that DID
   move, neither verb's caller-side bare-name repoint (gap 2 above)
   fires for the constant either, so the NameError shows up only inside
   a hypothesis @given property test's counterexample shrink, not at
   collection time.

5. SPLIT's PER-CHUNK IMPORT CARRY-FORWARD SCATTERS IMPORTS MID-FILE
   INSTEAD OF HOISTING TO THE TOP. Each chunk transaction (T-3122's
   needed_import_ops_for_symbols) inserts its own copy of whatever
   imports THAT chunk's moved class needs at the insertion point of
   that specific chunk -- across a 14-symbol --chunk-size 1 split
   landing all classes in the same destination file, this produced 5-15
   duplicate/scattered import statements per file (ruff E402 module-
   import-not-at-top-of-file), sometimes hundreds of lines below the
   file's real top. ruff --fix cannot repair E402 (needs semantic
   hoisting, not just reordering within a block); required a custom
   AST-based hoist-and-dedupe pass across all 14 split files by hand.

6. EVIDENCE-CITATION CARRY-FORWARD CAN WRITE THE WRONG DESTINATION
   FOR A LATER-CONSOLIDATED FILE. When a ticket's evidence/frob:tests
   citation is rewritten by the split's own transaction, it appears to
   bind to whatever chunk-transaction ran LAST for that class rather
   than the class's true final module -- 124 evidence citations across
   26 ticket.md files ended up all pointing at one particular
   destination file (test_land_core.py) regardless of which of 14
   files the cited class actually landed in. Root cause not confirmed
   (possibly a stale symbol->module index reused across chunk calls in
   the same split invocation, or a caching artifact from re-running
   split multiple times against overlapping symbol sets); reproduced
   twice, fixed by hand cross-checking every citation against the
   actual class definitions in the destination files. This one is the
   most dangerous of the six: it silently orphans OTHER tickets'
   evidence and only surfaces at land time via OrphanedEvidenceDeletion,
   not at split time.