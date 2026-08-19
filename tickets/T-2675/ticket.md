---
id: T-2675
title: test_derived_match hardcoded MIRRORED_LEDGER_VERBS set is stale after T-2624
state: queued
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
T-2624 (`feat(tickets): land T-2624 CLI wiring for runs_last_parallel_safe`)
added "runs-last-parallel-safe" to `LEDGER_VERB_STRATEGY`
(`src/frob/app/ticket_runner/_ledger_mirror.py`) as a
`GENERIC_COMMIT_MIRRORED` verb, but did not update
`tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy::test_derived_match`'s
hardcoded expected `MIRRORED_LEDGER_VERBS` set, which still lists the
pre-T-2624 16 verbs. Found and confirmed pre-existing (unrelated to my
own change) while working T-2570: the same failure reproduces against
main after merging it into a clean worktree, before any of my own edits.

Fix: add "runs-last-parallel-safe" to the expected frozenset in that
test.
