---
id: T-3535
title: 'macOS: identity-fallback test still sees the runner git identity; scrub system-level
  gitconfig too'
state: done
kind: bug
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record macOS-only BUG002 waiver per series instructions
  actor: logan
  at: '2026-08-31'
  old_length: 0
  new_length: 410
- mode: append
  reason: fix waiver directive format
  actor: logan
  at: '2026-08-31'
  old_length: 410
  new_length: 727
evidence:
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_identity_less_environment_falls_back_to_throwaway_git_identity
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: cc1d5592a8d7da0c03ac0c57f4e39b087e0069b2
---
frob:waive BUG002 -- macOS-only defect (ground-truth verified from CI run 33353658750 job 99371615032 log: assert 'Anka <runner...local>' == 'frob-bot <...>'); fix is hermetic (scrubs GIT_CONFIG_SYSTEM/GIT_CONFIG_NOSYSTEM/GIT_AUTHOR_*/GIT_COMMITTER_* unconditionally) but the defect itself only reproduces on a macOS runner with a real system-level gitconfig, so it cannot fail-then-pass on this Linux dev box.

frob:waive BUG002 reason="macOS-only defect, ground-truth verified from CI run 33353658750 job 99371615032 (assert Anka <runner...local> == frob-bot <...>); fix is hermetic but the defect itself only reproduces on a macOS runner with a real system-level gitconfig, so it cannot fail-then-pass on this Linux dev box"