---
id: T-5479
title: 'Windows-only: frob-suggest hook dedup-on-repeat fails (4 node ids)'
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
only. 4 failing node ids, all in tests/test_hook_frob_suggest.py:
- test_second_identical_check_pipeline_is_allowed_through
- test_second_identical_fleet_probe_is_allowed_through
- test_third_identical_command_is_blocked_again
- TestHandRenameEditMultifile::test_frob_suggest_ack_env_var_bypasses_it

Sample failure: test_second_identical_check_pipeline_is_allowed_through
expects a SECOND identical command to be silently allowed through (the
frob-suggest hook's own de-dup-on-repeat behavior) but gets the hook's
BLOCK response again, as if it were treated as a first-time/different
command. This points at the hook's "have I seen this exact command
before" cache/dedup key being computed differently on Windows -- likely a
path-separator or line-ending difference in the command string used as
the dedup key, so the same logical command hashes/matches differently
across two invocations on Windows.

Needs someone to read the frob-suggest hook's dedup-key implementation
with Windows path/newline normalization in mind; not root-caused further
in this drain pass.
