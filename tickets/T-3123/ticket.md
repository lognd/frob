---
id: T-3123
title: Stop FROB_WORKTREE leaking between tests in test_ticket_land.py
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_land.py
- tests/conftest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_a_leaves_frob_worktree_set_like_apply_agent_env_does
- tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_b_does_not_see_a_leaked_frob_worktree
- tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_apply_agent_env_leak_is_contained_to_its_own_test
- tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_must_stay_quiet_after_apply_agent_env_leak
designated_repro_test: null
acceptance:
- text: Given tests/test_ticket_land.py run as a whole file, when it completes, then
    zero tests fail with TicketError.WorktreeLeaseViolation
  evidence:
  - tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_a_leaves_frob_worktree_set_like_apply_agent_env_does
  - tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_b_does_not_see_a_leaked_frob_worktree
  - tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_apply_agent_env_leak_is_contained_to_its_own_test
  - tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_must_stay_quiet_after_apply_agent_env_leak
- text: Given a test that deliberately leaves FROB_WORKTREE set, when the next test
    in the same worker runs, then it is unaffected by the leaked value
  evidence:
  - tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_a_leaves_frob_worktree_set_like_apply_agent_env_does
  - tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_b_does_not_see_a_leaked_frob_worktree
  - tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_apply_agent_env_leak_is_contained_to_its_own_test
  - tests/test_ticket_land.py::TestWorktreeLeaseEnvIsolation::test_must_stay_quiet_after_apply_agent_env_leak
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: ef95d259946e90a84797f488b915ea8eb607d001
---
tests/test_ticket_land.py cannot host evidence that must RESOLVE, because
tests running after its `land()`-driven cases in the same worker refuse with
`TicketError.WorktreeLeaseViolation`:

  worktree-guard: agent leased to /tmp/.../wt-v2-a; refusing to mutate
  /tmp/.../main -- cd into the leased worktree, or clear FROB_WORKTREE if
  this is deliberate

MEASURED (2026-08-27, series BS, worktree series-bs):
- `uv run pytest tests/test_ticket_land.py -q` on an UNMODIFIED main:
  145 WorktreeLeaseViolation occurrences.
- Same file with T-3089's diff applied: 143-144. So this is entirely
  pre-existing and independent of that change.
- Every one of the failing node ids passes when run ALONE.

Root cause to confirm: a test (or a product call one makes) sets
`FROB_WORKTREE` in the pytest worker's own `os.environ` and never restores
it, so `_worktree_guard` then refuses every later test that mutates a
DIFFERENT tmp_path repo. The leaked lease named in the message
(`wt-v2-a`) is created by
`TestLedgerV2LandMergeStory::test_disjoint_v2_tickets_land_with_no_custom_merge`.

WHY THIS MATTERS BEYOND ANNOYANCE: this is a silent-zero of the kind the
repo already has doctrine about. A ticket binding evidence in this file
gets `EvidenceNotPassing` and an agent's natural reaction is to assume its
own change broke something, or to move the evidence somewhere it resolves
(which is what T-3089 did) -- the file's real coverage stops being usable
as evidence at all.

FIX DIRECTION: an autouse fixture that snapshots and restores the
FROB_WORKTREE / lease-relevant environment around every test in this
module (or, better, in tests/conftest.py so no other module can acquire the
same problem), plus a must-fire fixture that leaks the var deliberately and
asserts the next test is unaffected. Do NOT fix it by deleting or skipping
the tests that leak.