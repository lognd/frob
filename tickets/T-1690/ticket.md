---
id: T-1690
title: 'Symbolic attribution: map a red batch''s findings to the commit that caused
  them via graph reachability'
state: done
kind: feature
origin: agent
created: '2026-08-06'
priority: critical
blocked_by:
- T-1688
- T-1703
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/verify/_attribution.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets.md
- tests/unit/verify/test_attribution.py
- tests/unit/test_rapid_sweep.py
- src/frob/verify/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/verify/test_attribution.py
  reason: T-1690 needs new attribution unit tests plus rapid_sweep attribution-wiring
    tests
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: T-1690 needs new attribution unit tests plus rapid_sweep attribution-wiring
    tests
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/verify/__init__.py
  reason: editing __init__ to export the new attribution symbols alongside _attribution.py
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_caller_break_attributes_to_the_caller_commit
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_direct_touch_attributes_at_depth_zero
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_two_reaching_commits_is_unattributed
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_zero_reaching_commits_is_unattributed
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_missing_line_falls_back_to_whole_file_candidates
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_graph_unavailable_is_an_error_for_the_whole_batch
- tests/unit/test_rapid_sweep.py::TestTicketIsOpen::test_open_ticket_is_open
- tests/unit/test_rapid_sweep.py::TestTicketIsOpen::test_done_ticket_is_not_open
- tests/unit/test_rapid_sweep.py::TestTicketIsOpen::test_missing_ticket_is_not_open
- tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_empty_queue_returns_empty_mapping
- tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_attributed_and_unattributed_round_trip
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_attributed_to_open_ticket_is_not_refiled
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_attributed_to_closed_ticket_is_refiled
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_unattributed_is_filed
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_all_attributed_to_open_tickets_files_nothing
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
---
The hard part, and the leaf most likely to be got subtly wrong.

Tier 1 -- SET DIFF. T-1684's rolling baseline already yields new findings
as identities rather than a count. Upgrade the identity from
(rule, file) to (rule, SYMBOL): a file-level identity cannot survive a
refactor that moves a symbol between files, and reports the move itself
as a regression.

Tier 2 -- SYMBOLIC REACHABILITY. A finding anchored at symbol S
attributes to the batch commit whose touched symbol set REACHES S in the
reference graph. This is the leaf's whole substance and it must be
graph-resolved: "the commit that touched the same file" is the lexical
version, it is wrong whenever a change breaks a caller rather than the
callee, and it is precisely the shortcut to refuse.

Ambiguity is a first-class outcome, not a coin flip. Zero candidates,
or more than one, is UNATTRIBUTED -- a distinct state that hands off to
the bisect leaf. Never pick the newest commit as a tiebreak; a confident
wrong attribution costs more than an honest "unknown", because it sends
someone to read a diff that is not the cause.

Attributed findings are filed against the OWNING ticket where one is
still open, otherwise as a new high-priority bug naming the commit, the
symbol, and the reachability path that produced the attribution. Log the
path -- an attribution nobody can audit is an assertion, not evidence.

Acceptance: a synthetic batch where commit A breaks a caller of a symbol
commit B touched attributes to A, not B; a finding reachable from two
commits' touched sets reports UNATTRIBUTED rather than guessing.

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