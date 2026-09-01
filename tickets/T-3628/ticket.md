---
id: T-3628
title: 'ARCH102: split src/frob/process/_lock.py (12 exports, 3 clusters)'
state: in-progress
kind: feature
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
- src/frob/process/_lock.py
- tests/unit/test_process_lock.py
- src/frob/process/_derived_lock.py
- src/frob/process/_lock_msvcrt.py
- docs/modules/process.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/**/*process*lock*
  reason: narrow overbroad glob that phantom-matches T-3591s live lease on tests/ticket_land_suite/**;
    the real test file is tests/unit/test_process_lock.py
  actor: logan
  at: '2026-09-01'
- op: add
  glob: tests/unit/test_process_lock.py
  reason: narrow overbroad glob that phantom-matches T-3591s live lease on tests/ticket_land_suite/**;
    the real test file is tests/unit/test_process_lock.py
  actor: logan
  at: '2026-09-01'
- op: add
  glob: src/frob/process/_derived_lock.py
  reason: ARCH102 cluster-3 split creates these new destination modules; docs anchor
    already existed and moves with the symbols
  actor: logan
  at: '2026-09-01'
- op: add
  glob: src/frob/process/_lock_msvcrt.py
  reason: ARCH102 cluster-3 split creates these new destination modules; docs anchor
    already existed and moves with the symbols
  actor: logan
  at: '2026-09-01'
- op: add
  glob: docs/modules/process.md
  reason: ARCH102 cluster-3 split creates these new destination modules; docs anchor
    already existed and moves with the symbols
  actor: logan
  at: '2026-09-01'
body_changes:
- mode: append
  reason: record split plan before coding, per ticket instruction
  actor: logan
  at: '2026-09-01'
  old_length: 765
  new_length: 2455
- mode: append
  reason: record cluster1-complete + cluster3-partial (4/8) progress and the T-draft-d028adeb
    blocker for whoever resumes this worktree
  actor: logan
  at: '2026-09-01'
  old_length: 2871
  new_length: 4151
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
ARCH102: src/frob/process/_lock.py has 12 exports clustering into
roughly 3 concerns -- split it along those clusters. Write the split
plan (which exports go into which new module, and why) in this
ticket's body BEFORE coding. MUST use `uv run frob refactor split` /
`uv run frob refactor move-module` to perform the actual split, never
a hand-copy (standing user directive) -- append any tool gaps
encountered to T-3596. After the split, run a repo-wide import check
and `ty` type-check.

Scope: src/frob/process/_lock.py + its test file + any direct
importers whose import statement must be updated.

Previously specified but never filed (LandInProgress starvation
during a prior agent's ~45 min of retries); refiled now as part of
draining that starved backlog.


## Split plan (T-3628, ARCH102, 12 exports / 3 clusters)

Cluster 1 -- msvcrt low-level primitives (Windows-only blocking
acquire/release helpers the portable flock layer calls into):
  fcntl, msvcrt (module-level backend handles)
  _msvcrt_acquire_blocking
  _msvcrt_release
-> new module `frob.process._lock_msvcrt`  <!-- frob:waive DOC006 reason="planned future module name, not yet built by this still-open ticket" -->

Cluster 2 -- portable flock primitive (the cross-platform advisory-lock
primitive every OTHER module in this repo imports directly -- stays at
the original module path, `frob.process._lock`, since it is this
module's own most-imported surface and the natural "small stable core"
half of the split):
  PortableLockUnavailable
  lock_backend_available
  portable_flock_acquire
  _portable_flock_acquire_posix
  _portable_flock_acquire_windows
  portable_flock_release

Cluster 3 -- derived-state lock (the higher-level per-repo lock built
ON TOP of cluster 2's primitive, plus its own process-registry
bookkeeping):
  DerivedStateLockUnavailable
  _LOCK_REL, _lock_local, _process_registry_lock, _process_held_counts
  _INHERITED_LOCK_KEYS_ENV, _INHERITED_LOCK_KEYS_SEP
  held_registry_keys
  _worker_inherits_hold
  _process_already_holds
  _derived_lock_path
  _canonical_registry_key
  derived_state_lock
  derived_state_write_lock
-> new module `frob.process._derived_lock`  <!-- frob:waive DOC006 reason="planned future module name, not yet built by this still-open ticket" -->

Executed via `uv run frob refactor split src.frob.process._lock --symbols
<msvcrt names> --into frob.process._lock_msvcrt`, then a second split for
the derived-lock cluster `--into frob.process._derived_lock` -- never a
hand-copy. `_lock.py` keeps cluster 2 (the portable flock primitive) as
its own remaining content; the tool rewrites every importer's import
statement for the moved names.

## Unblock log
- 2026-09-01: unblocked by T-3596 -- T-3596 landed at 4fb806e3d03e; the move/split import-carry, bare-name-repoint, free-variable, and decorator-preservation gaps this split needs are fixed
- 2026-09-01: unblocked by T-draft-d028adeb -- T-draft-d028adeb was promoted to T-3650, which landed at b1435d44523d fixing the self-import carry-forward bug this ticket's remaining moves needed



## Progress note (blocked by T-draft-d028adeb)

Cluster 1 (msvcrt) COMPLETE and verified: frob.process._lock_msvcrt.py
created, _msvcrt_acquire_blocking/_msvcrt_release moved cleanly (real
import + all T-3596 structural checks pass).

Cluster 3 (derived-state-lock) PARTIALLY moved (4 of 8 symbols), each
individually verified (real import, decorators_preserved, no_self_import,
no_undefined_names all PASS): held_registry_keys, _worker_inherits_hold,
_process_already_holds, _derived_lock_path already live in
frob.process._derived_lock.py as of this worktree's HEAD.

Remaining 4 symbols (DerivedStateLockUnavailable, _canonical_registry_key,
derived_state_lock, derived_state_write_lock) cannot move -- every
attempt (full 8-symbol split, per-symbol move, 4-symbol split of just
the remainder) hits the circular import documented in T-draft-d028adeb
and rolls back cleanly (T-3596's own verify checks correctly refuse the
commit; nothing broken landed). Once T-draft-d028adeb's fix lands,
resume from this worktree's HEAD and move/split the remaining 4 symbols
-- the msvcrt cluster and the first 4 derived-lock symbols do not need
to be redone.

Cluster 2 (portable flock primitive) is untouched, staying at
frob.process._lock per the split plan -- it never needed a move.
