---
id: T-2394
title: an empty ticket scope is only caught at land time
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_setters.py
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/tickets/_new_renumber.py
- tests/test_tickets_no_scope.py
- docs/modules/tickets-lifecycle.md
- docs/modules/tickets-data-storage.md
- tests/unit/test_app_runners_batch7.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-2394: refuse an empty scope at frob ticket start, add a declared-no-scope
    escape hatch distinguishable from omission'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/tickets/_setters.py
  reason: 'T-2394: refuse an empty scope at frob ticket start, add a declared-no-scope
    escape hatch distinguishable from omission'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: 'T-2394: refuse an empty scope at frob ticket start, add a declared-no-scope
    escape hatch distinguishable from omission'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: 'T-2394: refuse an empty scope at frob ticket start, add a declared-no-scope
    escape hatch distinguishable from omission'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: 'T-2394: refuse an empty scope at frob ticket start, add a declared-no-scope
    escape hatch distinguishable from omission'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: 'T-2394: refuse an empty scope at frob ticket start, add a declared-no-scope
    escape hatch distinguishable from omission'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/config.py
  reason: 'T-2394: refuse an empty scope at frob ticket start, add a declared-no-scope
    escape hatch distinguishable from omission'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'T-2394: refuse an empty scope at frob ticket start, add a declared-no-scope
    escape hatch distinguishable from omission'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: 'T-2394: refuse an empty scope at frob ticket start, add a declared-no-scope
    escape hatch distinguishable from omission'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_tickets_no_scope.py
  reason: 'T-2394: refuse an empty scope at frob ticket start, add a declared-no-scope
    escape hatch distinguishable from omission'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: 'T-2394: doc the empty-scope refusal and declared-no-scope escape hatch'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: 'T-2394: doc the empty-scope refusal and declared-no-scope escape hatch'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: T-2394's new hard gate at start regresses existing fixtures here that create
    tickets with empty scope for unrelated purposes; give them real scope
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_tickets_no_scope.py::TestSetNoScopeDeclared::test_sets_both_fields
- tests/test_tickets_no_scope.py::TestSetNoScopeDeclared::test_reason_missing_refuses
- tests/test_tickets_no_scope.py::TestRefuseEmptyScopeOnStart::test_empty_scope_refuses
- tests/test_tickets_no_scope.py::TestRefuseEmptyScopeOnStart::test_declared_no_scope_starts_cleanly
- tests/test_tickets_no_scope.py::TestRefuseEmptyScopeOnStart::test_nonempty_scope_starts_cleanly
- tests/test_tickets_no_scope.py::TestRefuseEmptyScopeOnStart::test_full_start_cli_refuses_on_empty_undeclared_scope
- tests/test_tickets_no_scope.py::TestRefuseEmptyScopeOnStart::test_full_start_cli_succeeds_once_declared
- tests/test_tickets_no_scope.py::TestWarnEmptyScopeOnNew::test_empty_scope_warns_at_filing_time
- tests/test_tickets_no_scope.py::TestWarnEmptyScopeOnNew::test_declared_no_scope_is_silent
- tests/test_tickets_no_scope.py::TestWarnEmptyScopeOnNew::test_nonempty_scope_is_silent
- tests/test_tickets_no_scope.py::TestScopeCliDeclareNoScope::test_flag_survives_real_argv_parsing
- tests/test_tickets_no_scope.py::TestScopeCliDeclareNoScope::test_flag_absent_defaults_false
- tests/test_tickets_no_scope.py::TestRefuseEmptyScopeOnStart::test_scope_breadth_ack_does_not_satisfy_empty_scope_refusal
designated_repro_test: tests/test_tickets_no_scope.py::TestRefuseEmptyScopeOnStart::test_full_start_cli_refuses_on_empty_undeclared_scope
acceptance:
- text: Given an implementation ticket with an empty scope, when frob ticket start
    runs, then it refuses, rather than the omission surfacing hours later at land
    time.
  evidence:
  - tests/test_tickets_no_scope.py::TestRefuseEmptyScopeOnStart::test_full_start_cli_refuses_on_empty_undeclared_scope
- text: Given a ticket that legitimately has no file scope, when it declares that
    explicitly, then it starts cleanly and is distinguishable from one whose scope
    was merely omitted.
  evidence:
  - tests/test_tickets_no_scope.py::TestRefuseEmptyScopeOnStart::test_full_start_cli_succeeds_once_declared
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED TODAY: T-2358 was created with an EMPTY scope. Nothing
complained at creation, nothing complained at `ticket start`, and
nothing complained during hours of implementation work. It surfaced only
at LAND time, when the out-of-scope waive-deletion check refused, by
which point the agent had to reconstruct the scope from the files it had
already touched and disclose the change.

An empty scope is never correct for an implementation ticket: scope is
simultaneously the evidence-coverage declaration and the write lease, so
an empty one means the ticket holds no lease and its changes are
unattributable. The cost is paid at the most expensive possible moment.

FIX: refuse (or loudly warn on) an empty scope at `frob ticket new` for
implementation kinds, and refuse at `frob ticket start` unconditionally
-- start is the point where a lease is actually needed, so it is the
correct hard gate. Tickets that legitimately have no file scope (a
tier=epic rollup, a pure decision record) should be able to say so
explicitly rather than by omission, so an empty scope and a declared
no-scope are distinguishable. That distinction is the same
fail-loudly doctrine as T-2391: absence must be declared, not inferred
from silence.