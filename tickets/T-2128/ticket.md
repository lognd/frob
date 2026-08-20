---
id: T-2128
title: SCOPE002 for docs/modules/tickets.md#coalescing-verify-worker-t-1688 is ERROR-severity
  while every other SCOPE002 against this doc is a warning
state: in-progress
kind: bug
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- tickets/T-2684/**
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/
  reason: narrow to the single file containing SCOPE002's severity/message logic under
    investigation
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/gates/__init__.py
  reason: narrow to the single file containing SCOPE002's severity/message logic under
    investigation
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tickets/T-2684/**
  reason: standalone fix for a fabricated symbol citation in T-2684's body (frob.app._check_chunking._run_gate_chunks_stamping_progress
    does not exist; real symbol is _run_baseline_chunks), found via T-2311's docblocks
    run and confirmed by coordinator; landing alongside T-2128 rather than filing
    a one-line-fix ticket
  actor: logan
  at: '2026-08-19'
body_changes:
- mode: append
  reason: 'BUG002 needs a waiver for a not-reproducible investigation close: no code
    change was made because there was nothing left to fix'
  actor: logan
  at: '2026-08-19'
  old_length: 951
  new_length: 1491
evidence:
- tests/test_gates.py::TestScope002ClosureGate::test_silent_on_closed_scope
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob check --ticket <id> --only scope` reports 8 SCOPE002 ERRORS (not
warnings) for docs/modules/tickets.md#coalescing-verify-worker-t-1688's
frob:describes targets in src/frob/verify/_worker.py, for ANY ticket
whose scope declares docs/modules/tickets.md alone -- confirmed against
T-1973, which made ZERO content edits this session (a pure Done-report
closure), and still shows the identical 8 errors as T-1899/T-1952/
T-1996, which DID edit the doc. Every other SCOPE002 finding for the
same broad doc file reports as a WARNING (386 of them, same run) --
these 8 are the only ones promoted to ERROR, and the promotion is
unrelated to anything touched this session.

Pre-existing, not caused by any of T-1899/T-1952/T-1996/T-1973's own
work -- filed rather than silently worked around. Worth investigating
why this one anchor's SCOPE002 findings are ERROR-severity while every
sibling SCOPE002 finding against the same doc file is WARNING-severity.

<!-- frob:waive BUG002 reason="investigation-only closure: T-2128's own finding IS that the reported defect no longer reproduces at main (live-remeasured T-1973 -- 106/106 SCOPE002 findings are severity=warning, 0 error, 0 mention of _worker.py/coalescing-verify-worker at all). There is no live defect left to write a fails-at-main/passes-at-fix test for; the bound test (test_silent_on_closed_scope) demonstrates SCOPE002's current WARN-only behavior, which is the whole point of this closure, not a fix to a bug that still exists." -->