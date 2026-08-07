---
id: T-0789
title: uv.lock auto-resyncs frob version on every uv run in a worktree, causing spurious
  SCOPE001 unless manually reverted
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- pyproject.toml
- uv.lock
- Makefile
- tests/test_makefile_lock_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_makefile_lock_sync.py
  reason: 'T-0789: regression test asserting the upload Makefile recipe re-locks and
    commits uv.lock alongside a pyproject.toml version bump, so worktrees never start
    from a stale lock again.

    '
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_makefile_lock_sync.py::test_upload_relocks_after_version_bump
- tests/test_makefile_lock_sync.py::test_upload_commits_uv_lock_with_pyproject
designated_repro_test: null
threat: null
component: null
---
Observed while working T-0704 (worktree agent-ad82d24588b5083b6, 2026-07-22/23). This worktree's checked-in uv.lock records frob's own package version as 0.97.0 while pyproject.toml's version line is already 0.98.0 (a pre-existing mismatch present at the worktree's own base commit, not introduced by any ticket worked in this session). Because uv.lock is not scope-locked against auto-sync, EVERY `uv run ...` invocation (including read-only ones like `frob ticket show` or `frob check`) silently rewrites uv.lock's frob version line to match pyproject.toml, leaving a working-tree modification an agent must notice and `git checkout HEAD -- uv.lock` away before every commit/check -- and if missed, SCOPE001 fires (uv.lock outside the ticket's declared scope) on every subsequent `frob check` even though no agent hand-edited the file. Section 4b of docs/guides/agent-playbook.md already forbids agents from touching uv.lock by hand, but does not cover this auto-touch-by-tooling case. Fix: either (a) make `uv run`'s auto-sync a no-op when only the local version-line mismatch is the cause (uv config: --frozen or --no-sync for frob's own CLI invocations, or a repo-level uv setting), or (b) have the section-4b agent-file-blacklist pre-commit hook silently discard/reset a version-line-only uv.lock diff caused by this sync rather than warning/blocking, or (c) reconcile pyproject.toml/uv.lock at land time so fresh worktrees never start with the mismatch. Any one of the three removes the recurring "revert uv.lock before committing" step every worktree agent currently has to remember.