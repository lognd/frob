---
id: T-3628
title: 'ARCH102: split src/frob/process/_lock.py (12 exports, 3 clusters)'
state: in-progress
kind: feature
origin: human
created: '2026-09-01'
priority: medium
blocked_by:
- T-3596
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
-> new module `frob.process._lock_msvcrt`

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
-> new module `frob.process._derived_lock`

Executed via `uv run frob refactor split src.frob.process._lock --symbols
<msvcrt names> --into frob.process._lock_msvcrt`, then a second split for
the derived-lock cluster `--into frob.process._derived_lock` -- never a
hand-copy. `_lock.py` keeps cluster 2 (the portable flock primitive) as
its own remaining content; the tool rewrites every importer's import
statement for the moved names.
