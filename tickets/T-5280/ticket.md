---
id: T-5280
title: frob ticket points/tokens missing LEDGER_VERB_STRATEGY entry (T-5132 regression)
state: done
kind: bug
origin: human
created: '2026-09-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: 5
unsized_ack: true
unsized_ack_reason: test reason
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_ledger_mirror.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
evidence:
- tests/unit/test_ticket_runner_ledger_mirror.py::TestAutoCommitDispatchCoversEveryStrategy::test_every_strategy_member_is_covered
- tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy::test_all_classified
designated_repro_test: tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy::test_all_classified
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob
branch: dev
---
T-5132 landed frob ticket points/tokens verbs but never registered them in _ledger_mirror.LEDGER_VERB_STRATEGY (T-2603) -- _ledger_mirror.py was not in T-5132's declared scope. Every frob ticket points/tokens invocation currently crashes with 'has no LEDGER_VERB_STRATEGY entry'. Fix: add both verbs as GENERIC_COMMIT_MIRRORED, same as milestone/priority.