---
id: T-3660
title: 'refactor split/move: reexport-shim + free-var carry-forward creates unavoidable
  circular import when a real caller already imports the destination directly'
state: queued
kind: bug
origin: human
created: '2026-09-01'
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
Found while working T-3628 (ARCH102 split of src/frob/process/_lock.py,
derived-state-lock cluster), using T-3596's already-landed fixes.

T-3596 fixed gaps 1-4 (import carry-forward, bare-name repoint,
module-level free-variable carry-forward, decorator preservation) --
all four now verified working, including a positive-control split of
the exact previously-corrupting derived_state_lock/@contextmanager
function (decorators_preserved: PASS every time).

A FIFTH gap surfaced, distinct from all four: when (a) a moved
function's body needs a free variable that stays in the SOURCE module
(gap 3's own fix: needed_import_ops_for_symbols emits a synthetic
"from source_module import name" at the TOP of the destination file),
AND (b) the source module keeps a re-export shim for the moved name
(split's own build_reexport_shim_op, appended at the SOURCE file's own
END) so already-repointed external callers of the OLD path still work,
AND (c) at least one real caller now imports the DESTINATION module
directly (either because scan_references already repointed it, or it
always did) -- the two modules form a genuine, unavoidable circular
import:

  entering frob.process._derived_lock first (a real caller does this,
  since frob.check.__init__ already imports "from frob.process.
  _derived_lock import derived_state_lock" after an earlier successful
  move repointed it) ->
  _derived_lock.py's own TOP-level import needs "_process_held_counts,
  _process_registry_lock" from frob.process._lock ->
  begins importing frob.process._lock fresh ->
  _lock.py executes its own body, reaches its OWN re-export shim
  ("from frob.process._derived_lock import (...)") ->
  frob.process._derived_lock is ALREADY in sys.modules (mid-import,
  only past its own top-level imports, has not yet defined the names
  the shim wants) ->
  ImportError: cannot import name '...' from partially initialized
  module 'frob.process._derived_lock' (circular import)

Reproduced 3 times against this exact checkout (fbe638113-family base
+ T-3596's landed commit 4fb806e3d03e): a full 8-symbol split of the
derived-lock cluster, a per-symbol move for individual members of
that same cluster, and a 4-symbol split for the cluster's remainder
after 4 members had already moved cleanly -- all three roll back
cleanly (T-3596's own verify_module_import + verify_no_self_import
correctly catch it and refuse to commit; NO corruption reached main),
but none can complete the split.

Not a regression of T-3596's own fixes -- gaps 1-4 are all independently
confirmed still fixed (decorators_preserved and the free-var carry each
passed on every attempt). This is a NEW interaction between two
by-design mechanisms (the shim in one direction, the free-var carry in
the other) that neither gap's own fix, nor split's original T-1201
design, accounted for.

SUGGESTION: either (a) skip generating a re-export shim entry for a
name that scan_references already found and repointed EVERY external
caller of (making the shim's coverage of that specific name genuinely
redundant, not just defensive), so the source module never re-imports
back from the destination at all when nothing needs it to; or (b) make
the free-var carry-forward import LAZY (inside each moved function
body, not at module top-level) so the destination module's own import
doesn't force a full source-module execution before either module has
defined what the other needs; or (c) detect this specific cycle shape
at Plan time (both modules' own needed-import sets reference each
other) and refuse before ever attempting to apply, with a clear message
naming the two symbols in tension, rather than relying on Verify's
after-the-fact import to catch it (which it does correctly, but only
after a full plan/apply/rollback cycle).
