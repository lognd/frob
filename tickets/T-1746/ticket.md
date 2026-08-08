---
id: T-1746
title: Implement real fix for WIRE001 same-file test-fixture reuse false positive
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_tickets_mutation_evidence.py
- src/frob/gates/_wire.py
- tests/test_gates.py
- tickets/archive/T-1558/ticket.md
- src/frob/gates/_waive.py
- design/frob.strata
- tickets/T-1746/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: the T-1746 rule change (same-file test_* callers now count as reached) directly
    conflicts with test_test_helper_called_only_from_its_own_defining_file_is_still_flagged's
    locked-in old-behavior assertion; that test must be updated to match the new,
    intentionally more permissive rule
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/archive/T-1558/ticket.md
  reason: T-1746 renamed the WIRE001 test T-1558's own evidence citation points at
    (test_test_helper_called_only_from_its_own_defining_file_is_still_flagged -> split
    into two tests reflecting the new same-file-test-caller rule); update the stale
    citation
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'COV002 leftover from T-1764''s own commit: _waive004_dead_count_by_rule
    needs its own frob:ticket edge'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: 'COV002 leftover from T-1764: gates node interface change needs its own
    frob:ticket edge'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1746/**
  reason: SCOPE001 flags the ticket's own ticket.md/done-report.md under v2 storage
    (same fix T-1719/T-1764 needed)
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_gates.py::TestWireGate::test_test_helper_called_from_a_real_test_in_the_same_file_is_not_flagged
- tests/test_gates.py::TestWireGate::test_test_helper_called_only_from_a_non_test_helper_is_still_flagged
designated_repro_test: null
threat: null
component: null
---
`tests/test_tickets_mutation_evidence.py::_repo_with_add_change` carries
a `frob:waive WIRE001` (T-1727's own land) because WIRE001's same-file
exclusion rule (T-1592/T-1558's precedent: a test-tree symbol's OWN
defining file never counts as a "reached" caller, only a DIFFERENT test
file does) does not recognize a shared fixture helper reused by two
test classes within one file as wired, even though every call site is a
real `test_*` method, verifiable by reading the file directly.

Two ways to close this honestly:
1. Move `_repo_with_add_change` to a location a genuinely different
   test file could plausibly reuse (a shared fixtures module), so a real
   cross-file caller exists and the waiver can be dropped.
2. If same-file test-fixture reuse is a legitimate, common shape (it
   plausibly is -- DUP001 actively REQUIRES this exact extraction
   whenever two test classes in one file develop near-identical setup
   bodies), extend WIRE001's `_wire_test_path_excluded` same-file rule
   to also recognize a call from ANY `test_*`-prefixed function/method
   in the SAME file as a genuine reach class, not just cross-file reuse.

Either fix removes the T-1727 waiver's need to exist.