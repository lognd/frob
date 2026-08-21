---
id: T-2791
title: test_derived_match hardcoded verb set is stale (missing unblock/runs-last-parallel-safe/set-parent)
state: queued
kind: bug
origin: human
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_ticket_runner_ledger_mirror.py
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
Found while working T-2780: TestVerbStrategy.test_derived_match hardcodes the expected MIRRORED_LEDGER_VERBS/OWN_TRANSACTION_VERBS set literally; it is stale on main (pre-existing, unrelated to T-2780/T-2770/T-2624/T-2681) missing 'unblock', 'runs-last-parallel-safe', and 'set-parent'. Fix: derive the expected set from LEDGER_VERB_STRATEGY the same way test_all_classified does, or update the literal.