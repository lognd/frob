---
id: T-1689
title: 'Batch test selection: run a batch''s union touched-set in one pytest process'
state: done
kind: feature
origin: agent
created: '2026-08-06'
priority: high
blocked_by:
- T-1687
parent: T-1686
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify/_selection.py
- src/frob/app/graph_runner.py
- docs/modules/tickets.md
- tests/unit/verify/test_selection.py
- docs/modules/app.md
- tests/unit/verify/conftest.py
- tests/unit/verify/test_attribution.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/verify/test_selection.py
  reason: unit tests for the new batch selection module live in tests/unit/verify/
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/app.md
  reason: AFFECT001 requires docs/modules/app.md#runners touched alongside graph_runner.py::run's
    changed dispatch table
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/verify/conftest.py
  reason: shared _symbol/_entry test helper extracted here to avoid DUP001 with test_attribution.py
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/verify/test_attribution.py
  reason: 'DUP001: dedupe _symbol/_entry against the new shared conftest.py helper'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/verify/test_selection.py::TestSelectBatchTests::test_union_of_two_entries_selects_once
- tests/unit/verify/test_selection.py::TestSelectBatchTests::test_empty_batch_selects_nothing
- tests/unit/verify/test_selection.py::TestSelectBatchTests::test_unresolvable_symbol_is_skipped_not_fatal
- tests/unit/verify/test_selection.py::TestRunBatchSelectedTests::test_graph_unavailable_is_an_error
- tests/unit/verify/test_selection.py::TestRunBatchSelectedTests::test_selects_and_runs_once
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
---
The second, independent half of the batching saving. The gate pass
amortises N-to-1 by coalescing; the TEST run amortises by selection.

Compute the batch's affected test set as the union of its entries'
touched symbol sets expanded through the reference graph to the tests
that reach them -- symbolic reachability, never "tests whose filename
resembles the changed module". Run that union in ONE pytest process: one
collection, one conftest evaluation, one set of session fixtures.

N separate `frob test` invocations over overlapping touched sets pay N
cold pytest startups and re-run every shared test once per ticket. The
union pays one startup and runs each test once. On a batch of five
tickets touching adjacent modules this is usually the larger of the two
savings in this epic.

Report what was selected AND what was excluded, with counts, at INFO. A
selection that silently narrows is indistinguishable from a suite that
passes -- if the selection cannot be computed (graph unavailable), fall
back to the full suite and say so loudly, never to a narrower set.

Acceptance: a batch of tickets with overlapping touched sets runs each
affected test exactly once in a single process; an unresolvable graph
falls back to the full suite with an explicit WARNING naming why.

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.