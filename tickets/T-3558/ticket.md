---
id: T-3558
title: WIRE001 analyzer call-graph misses multiprocessing.Process target= references
state: queued
kind: bug
origin: human
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_fix_engine_journal.py
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
found while closing T-3534: tests/unit/test_fix_engine_journal.py carries a frob:waive WIRE001 with follow_up=T-3534 for _write_journal_and_block, which is genuinely wired via multiprocessing.Process's target= kwarg in TestAbandonedAutofixJournalSigkillSubprocess.test_sigkilled_journal_writer_is_detected_and_refused -- the call-graph analyzer does not resolve a target= reference the way it resolves a direct call, so this waiver is load-bearing until the analyzer is taught to follow target= kwargs (or an equivalent annotation convention is added). T-3534 was a docs-only ticket (docs/modules/gates.md) and cannot carry this follow_up; re-pointing the waiver's follow_up to this ticket instead.