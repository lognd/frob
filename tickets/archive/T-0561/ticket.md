---
id: T-0561
title: 'test-scope-lease: broad tests/** lease on an in-progress epic blocks any other
  ticket from adding a test'
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/
- tests/test_tickets_scope_mutation.py
- src/frob/gates/_parse_failures.py
- src/frob/graph/__init__.py
- src/frob/graph/_models.py
- tests/test_gates.py
- tests/test_graph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_scope_mutation.py
  reason: T-0561 regression tests for the new-file lease carve-out
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/gates/_parse_failures.py
  reason: re-tag COV002-flagged symbols with T-0561 now that T-0558 (their own ticket)
    is closed -- same precedent as T-0543's Done report
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/graph/__init__.py
  reason: same re-tag reason
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/graph/_models.py
  reason: same re-tag reason
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_gates.py
  reason: same re-tag reason
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_graph.py
  reason: same re-tag reason
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_new_file_under_broad_lease_is_exempt
- tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_existing_file_under_broad_lease_still_conflicts
- tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_non_test_file_under_broad_lease_still_conflicts
- tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_new_file_exact_match_of_holder_scope_still_conflicts
designated_repro_test: null
threat: null
component: null
---
found while working T-0546: frob ticket scope --add tests/unit/test_app_runners_batch6.py was rejected with ScopeLeaseConflict because T-0160 holds an in-progress lease over tests/** (a repo-wide coverage-backlog epic). Any other in-flight ticket that needs to add ONE new regression test anywhere under tests/ while such a broad epic is open is structurally blocked from landing a dedicated test for its own fix, and must fall back to binding frob:tests to a pre-existing test instead (weaker evidence). Fix direction: scope-lease conflict check should allow a narrower --add glob (a single new file, or a file the broader ticket has not itself touched) to coexist with a broader in-progress lease, or provide an explicit narrow-carve-out mechanism, rather than a blanket reject on any overlap.