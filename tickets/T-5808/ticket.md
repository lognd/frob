---
id: T-5808
title: 'land: reuse built native extensions when the crate tree hash is unchanged'
state: in-progress
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob
branch: dev
scope:
- src/frob/natives/_build.py
- tests/unit/test_natives_build.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/natives/_build.py
  reason: reuse a built native extension when the crate tree digest is unchanged,
    instead of always rebuilding
  actor: logan
  at: '2026-09-25'
- op: add
  glob: tests/unit/test_natives_build.py
  reason: fix existing test fakes for the new rustc --version toolchain-id spawn,
    plus new reuse tests
  actor: logan
  at: '2026-09-25'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured on every land today: "worktree natives stale/unimportable after
auto-rebuild attempt (T-1578)" followed by a maturin build of
strata_core and frob_core, 70-190 s per land, even when the worktree's
Rust sources are byte-identical to the root's already-built extension.
Fix: stamp each built extension with the git tree hash of its crate
source (`git rev-parse HEAD:strata-core/src`, same for frob-core) plus
the toolchain id; at land (and in `frob natives build`), when the
worktree's crate tree hash equals the stamp of an importable build in
the root venv (or the worktree's own venv), copy/reuse that artifact
instead of rebuilding; rebuild only on hash mismatch or import failure.
Positive control: two consecutive lands of worktrees with identical
crate trees must show one build and one reuse in the log; a worktree
that changes strata-core/src must rebuild. Owner directive: guaranteed-
safe automation runs automatically and is logged.
