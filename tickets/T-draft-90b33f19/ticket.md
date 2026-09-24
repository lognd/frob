---
id: T-draft-90b33f19
title: 'land: evidence re-verification spawn must not uv-sync after the post-squash
  natives rebuild'
state: in-progress
kind: bug
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-draft-90b33f19
branch: t-draft-90b33f19
scope:
- tests/unit/test_land_verify_natives.py
- src/frob/testing/_runners.py
- tests/unit/test_testing_runners_no_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/_land_verify.py
  reason: 'coordinator review: os.environ mutation trips SELFAUDIT001 (tickets_ledger
    node undeclared env.read/env.write); real fix moves to argv construction in frob.testing._runners,
    the actual uv run pytest spawn site'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/testing/_runners.py
  reason: the actual uv run pytest argv is built here (_build_runner_argv/_run_one_runner)
    -- insert --no-sync right after run for a uv-based declared test.runner command
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_testing_runners_no_sync.py
  reason: new test file for the argv --no-sync insertion fix
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured while landing T-3010: with T-5518 (_rebuild_stale_worktree_natives)
on dev, `frob ticket land T-3010 --dry-run --allow-cross-ticket` still
failed with "evidence did not pass post-merge" on the first attempt --
every evidence test importing milestone_closure_check failed
individually, identical to T-5518's own before-fix symptom. Setting
UV_NO_SYNC=1 on the `frob ticket land` invocation itself made the same
dry-run pass clean with no other change.

Root cause: T-5518's rebuild happens in-process (maturin develop into
the worktree's .venv site-packages), but _reverify_evidence_post_merge's
own evidence spawn (`_land_collected_fn`/`_land_passed_fn`) runs via
`uv run pytest`, and `uv run`'s own default auto-sync step reinstalls the
project's cached wheel (same declared version, unchanged pyproject.toml
version pin) OVER the freshly-built extension right before pytest
imports it -- so the rebuild that just ran is immediately undone by the
spawn that is supposed to observe it.

Fix: the uv run pytest spawn built in _reverify_evidence_post_merge (and
any sibling land-time evidence/test spawn using the same pattern) must
pass --no-sync to uv run, or set UV_NO_SYNC=1 in the child environment,
right after _rebuild_stale_worktree_natives runs -- so the rebuild it
just performed is the one the spawn actually imports.
