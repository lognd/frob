---
id: T-6527
title: 'Windows self-gate: pytest-node-shaped stray paths hit WinError2 stat failures'
state: queued
kind: bug
origin: agent
created: '2026-09-25'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/process/_derived_lock.py
- tests/unit/test_process_lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob
  reason: narrow from whole-tree scope to the one malformed frob:tests directive file
    this ticket fixes; src/frob/tickets/_land.py's matching directives are leased
    by in-progress T-5161, filed separately
  actor: logan
  at: '2026-09-25'
- op: add
  glob: src/frob/process/_derived_lock.py
  reason: narrow from whole-tree scope to the one malformed frob:tests directive file
    this ticket fixes; src/frob/tickets/_land.py's matching directives are leased
    by in-progress T-5161, filed separately
  actor: logan
  at: '2026-09-25'
- op: add
  glob: tests/unit/test_process_lock.py
  reason: narrow from whole-tree scope to the one malformed frob:tests directive file
    this ticket fixes; src/frob/tickets/_land.py's matching directives are leased
    by in-progress T-5161, filed separately
  actor: logan
  at: '2026-09-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 36173008509 (dev 473cee7656), windows-latest
job only, "frob check (self-gate)" step.

The self-gate parse pass tries to stat pytest node-id-shaped paths that do
not exist as files, e.g.:

  ERROR: failed to stat D:\a\frob\frob\TestDerivedStateWriteLock.test_standalone_rebuild_takes_exclusive:
  [WinError 2] The system cannot find the file specified
  WARNING: no grammar registered for extension '.test_standalone_rebuild_takes_exclusive'

and similarly for TestLandLockWaitBudgetFromDeclaredDeadline.test_no_declaration_keeps_the_flat_timeout_unchanged.
These look like pytest ids that leaked into a file-list the self-gate scans
(e.g. from a --lf/failed-node cache, coverage artifact, or a git-status
diff computed against a stale worktree state on this runner), rather than
real paths. This is a different symptom from T-5812 (cache.db lock-wait
"holder detection unsupported on this platform") but hits the same
Windows self-gate step and may share a root cause in how the step builds
its target file list on Windows.

Proposed fix: find where the self-gate step (or its parse-artifacts cache)
derives its file list on Windows and filter out non-path-shaped entries
before handing them to the stat/parse call; needs windows-latest (or
winrun) to reproduce.
