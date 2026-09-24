---
id: T-5481
title: 'Windows-only: land CAS ledger retry/compose fails (2 node ids)'
state: queued
kind: bug
origin: agent
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
worktree: null
branch: null
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
Found while draining CI run 35951365410 (dev 9e0c89bb19), windows-latest job
only. 2 failing node ids:
- tests/unit/test_land_cas_ledger_retry.py::TestRebaseComposedCommitOnto::test_rebased_commit_carries_the_same_content_change
- tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_ledger_only_cas_miss_rebases_and_retries_without_regates

Both fail with Err(LandComposeError.ComposeFailed) where Ok is expected --
the land-compose/rebase-onto machinery itself is failing under test on
Windows, not a downstream assertion. Plausible causes: git rebase
behaving differently on Windows (line-ending/autocrlf interaction), or a
path-separator assumption in the compose step itself. Needs the actual
captured error detail (not visible in the short summary this drain pass
extracted) before root-causing further.
