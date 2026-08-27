---
id: T-3035
title: ticket-leases dispatch-table fixture missing --reason for mutate verbs (5 tests)
state: queued
kind: bug
origin: human
created: '2026-08-26'
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
Linux full-suite triage (T-2992): 5 tests in
tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable
fail, all in the mutate-verb dispatch table used to check every
ticket-mutation verb auto-commits and leaves the repo clean:

  tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for
  tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[component]
  tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[kind]
  tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[priority]
  tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[tier]

CONFIRMED for [tier] and [component]: `frob ticket tier`/`frob ticket
component` (the mutate-verb CLI) now hard-refuses with `SystemExit: 1`
via `src/frob/app/ticket_runner/_mutate.py:939` ("frob ticket tier
requires --reason TEXT or --reason-file PATH") because the shared
dispatch-table fixture in this test file invokes the verb WITHOUT a
`--reason`. Whichever verbs in the parametrized table require `--reason`
today, the fixture's invocation for those verbs is stale.

Same root-cause class as the T-2394 empty-scope fixture drift (see the
sibling ticket for the ticket-lifecycle CLI cluster) -- this is a
different guard (a `--reason` requirement on mutate-style ticket verbs)
tripping a different, older shared test fixture (the dispatch table in
this one file). Test-fragility, not confirmed as a product regression.

FIX DIRECTION: update the dispatch table's per-verb invocation args to
include `--reason "test"` (or equivalent) for every verb the CLI now
requires it for, then re-run all 5 node ids above.
