---
id: T-2395
title: 'scope contention is undiscoverable: no way to ask which files are declared
  by many open tickets'
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_query.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/_cli_parsers/_ticket/_query.py
- tests/unit/test_app_runners_t2395_contention.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: implementing frob ticket contention per T-2395 body
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: implementing frob ticket contention per T-2395 body
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_query.py
  reason: implementing frob ticket contention per T-2395 body
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_app_runners_t2395_contention.py
  reason: implementing frob ticket contention per T-2395 body
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets.md
  reason: implementing frob ticket contention per T-2395 body
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_plain_render_ranks_and_names_owners
- tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_zero_contention_is_explicit_not_silent
- tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_json_render_shape
- tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_suggested_batching_is_transitive_across_files
- tests/unit/test_app_runners_t2395_contention.py::TestDoableHotFileMarker::test_doable_row_carries_hot_file_marker
- tests/unit/test_app_runners_t2395_contention.py::TestDoableHotFileMarker::test_doable_row_has_no_marker_without_contention
designated_repro_test: null
acceptance:
- text: Given a ledger where several open tickets declare the same file, when frob
    ticket contention runs, then it reports each contended file ranked by ticket count
    with the owning ticket ids and a suggested single-agent batching.
  evidence:
  - tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_plain_render_ranks_and_names_owners
  - tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_zero_contention_is_explicit_not_silent
  - tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_json_render_shape
  - tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_suggested_batching_is_transitive_across_files
  - tests/unit/test_app_runners_t2395_contention.py::TestDoableHotFileMarker::test_doable_row_carries_hot_file_marker
  - tests/unit/test_app_runners_t2395_contention.py::TestDoableHotFileMarker::test_doable_row_has_no_marker_without_contention
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: 71341c48f88747c52dcdcbf7762eb797f3f06c7d
---
MEASURED TODAY: `src/frob/__main__.py` is declared by NINE queued
tickets simultaneously (T-2385, T-1135, T-1608, T-1609, T-1614, T-1656,
T-1661, T-1945, plus the never-close anchor T-1831), and
`src/frob/app/_config_external.py` by six (T-1656, T-1661, T-1666,
T-1945, T-2202, T-2387).

I discovered this ONLY as a side effect of `frob ticket new` printing
overlap warnings while filing an unrelated ticket. There is no way to
ASK the question. Consequences paid today: two tickets were
double-assigned to different agents earlier in this drive, and a series
had to be re-routed mid-flight when the contention was noticed by luck.

Because scope is a write lease, contention directly caps parallelism --
it determines how many agents can work at once, which is the single
most important number for a drain drive. It should not be discoverable
only by accident.

FIX: `frob ticket contention` -- report files declared by 2+ open
tickets, ranked by ticket count, with the ticket ids per file and a
suggested batching (the set of tickets that should go to ONE agent
because they share a lease). Complements `frob ticket wave --agents N`,
which already computes scope-disjoint groups: wave answers "how do I
split work", contention answers "where is work already colliding".
Per the automatic-over-commands directive, also surface a warning in
`frob ticket doable` when a returned ticket sits on a hot file, so an
operator who never runs the new verb still sees it.