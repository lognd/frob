---
id: T-3676
title: 'self-gate floor (b): SEC110 waivers in test_wip.py FROB_WORKTREE reads'
state: in-progress
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
- tests/ticket_land_suite/test_wip.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 remedy: this is a directive-comment-only fix'
  actor: logan
  at: '2026-09-01'
  old_length: 837
  new_length: 945
evidence:
- tests/ticket_land_suite/test_wip.py::TestWorktreeLeaseEnvIsolation::test_a_leaves_frob_worktree_set_like_apply_agent_env_does
- tests/ticket_land_suite/test_wip.py::TestWorktreeLeaseEnvIsolation::test_b_does_not_see_a_leaked_frob_worktree
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Self-gate floor bucket (b): SEC110 waivers.

The bucket-list body assumed the 5 SEC110 findings were in
.claude/hooks/*.py; the current evidence log (scratchpad/ub-33545.log,
lines around 3033-3037) places all 5 in
tests/ticket_land_suite/test_wip.py:236,237,249,264,286 -- every read is
of FROB_WORKTREE, the worktree-path env var T-3123's leak-isolation
tests deliberately read/write directly (bypassing monkeypatch) to prove
tests/conftest.py's autouse fixture actually isolates it. FROB_WORKTREE
carries a local filesystem path, no secret.

Fix: add `frob:waive SEC110 reason="..."` directives at each of the 5
sites (FROB_WORKTREE carries no secret -- a worktree path, not
credential material).

Evidence: `timeout 540 uv run frob check --only secrets` (or whatever
--only name maps to the SEC family) shows 0 SEC110 for this file.


frob:no-behavior-change reason="comment-only fix: adds frob:waive directives, no runtime behavior touched"