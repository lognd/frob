---
id: T-3098
title: reopen verb missing from TestLedgerAutoCommitEnumeratedOverDispatchTable's
  exhaustiveness buckets
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while re-verifying T-3080's own touched-set tests (tests/test_ticket_leases.py
is in T-3080's declared scope). test_dispatch_table_verbs_are_all_accounted_for
fails at HEAD (unrelated to T-3080's own diff): T-3087's land added a `reopen`
verb to `frob.app.ticket_runner`'s dispatch table but did not add it to any of
`TestLedgerAutoCommitEnumeratedOverDispatchTable`'s own exhaustiveness buckets
(_MUTATING_VERB_INVOCATIONS / _READ_ONLY_VERBS / _NEEDS_DEDICATED_FIXTURE /
_LEDGER_TRANSACTIONAL_VERBS).

Confirmed pre-existing: `git stash` (none), the failure reproduces on main at
the commit T-3087 landed, before any of this ticket's own edits.

FIX DIRECTION: classify `reopen` into the correct bucket (it mutates the
ledger, so almost certainly _MUTATING_VERB_INVOCATIONS with a real invocation
fixture, unless it needs _NEEDS_DEDICATED_FIXTURE) and add the missing
accounting entry.
