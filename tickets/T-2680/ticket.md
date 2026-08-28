---
id: T-2680
title: playbook 5b's FROB_WORKTREE/FROB_AGENT leak fix only covers tests/system/**,
  not direct land()/new_ticket() calls elsewhere
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/agent-playbook.md
- docs/guides/agent-playbook-appendix.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/guides/agent-playbook-appendix.md
  reason: content moved here by T-2909; must correct the tests/system/** scoping claim
    per T-2680
  actor: logan
  at: '2026-08-27'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): the underlying code gap this bug ticket describes
    was already closed by T-3145''s repo-wide conftest fixture (confirmed: TestSigkillMidStaging
    passes under an ambient lease env at the parent commit too); this ticket''s only
    change is a doc correction to a stale claim in agent-playbook-appendix.md, with
    no runtime behavior delta of its own to reproduce as fail-then-pass'
  actor: logan
  at: '2026-08-27'
  old_length: 1539
  new_length: 1943
evidence:
- tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry
- tests/test_ticket_land.py::TestSigkillMidStaging::test_unrelated_land_does_not_absorb_a_killed_lands_staged_content
- tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_during_finalize_close_leaves_ticket_recoverable_not_a_silent_lie
- tests/test_ticket_land.py::TestSigkillMidStaging::test_normal_land_reaches_done_exactly_once_no_extra_transition
- tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_during_post_squash_reverification_leaves_ticket_recoverable
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 2580414e9846df72db383e7213bfc39ed2ce9b6d
---
Playbook section 5b (agent-playbook.md) states the T-0880 fix means "you
do not need to unset your shell's lease env before recording evidence
for tests/system/** tickets; the helper handles it" -- but that fix is
scoped to tests/system/conftest.py's own run() subprocess helper only.

tests/test_ticket_land.py's TestSigkillMidStaging class (and likely
other test files that call frob.tickets._land.land()/new_ticket()
directly as Python calls, not via a subprocess) inherit os.environ
unfiltered. If the invoking shell has FROB_WORKTREE/FROB_AGENT exported
(true for any dispatched worktree agent per T-0574), these direct calls
trip the worktree-lease guard against the WRONG cwd (the test's own
tmp_path fixture repo, not the leased worktree), failing with
WorktreeLeaseViolation.

Observed directly while working T-2564: `uv run frob ticket evidence`
(which spawns pytest as a subprocess with FROB_WORKTREE/FROB_AGENT
still exported in the calling shell) failed both
TestSigkillMidStaging tests with WorktreeLeaseViolation; unsetting
FROB_WORKTREE/FROB_AGENT in the invoking shell before the same command
fixed it immediately.

Fix candidates: either broaden the T-0880 environment-stripping fix to
cover tests/test_ticket_land.py's own subprocess/direct-call test
helpers (if pytest itself is spawned as a subprocess by some evidence-
recording paths), or correct playbook section 5b to scope its claim
accurately to tests/system/** only, not stated as blanket "you do not
need to unset your shell's lease env" without qualification.

frob:no-behavior-change reason="the underlying code gap this bug ticket describes was already closed by T-3145's repo-wide conftest fixture (confirmed: TestSigkillMidStaging passes under an ambient lease env at the parent commit too); this ticket's only change is a doc correction to a stale claim in agent-playbook-appendix.md, with no runtime behavior delta of its own to reproduce as fail-then-pass"