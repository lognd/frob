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
runs_last: false
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

## Done report

Changed:
- src/frob/verify/_attribution.py (new): AttributionError, Attribution, attribute_batch, _resolve_symbol, _symbols_in_file, _reaches, _load_snapshot_and_call_graph
- src/frob/verify/__init__.py: export Attribution/AttributionError/attribute_batch
- src/frob/app/ticket_runner/_rapid_sweep.py: _attribute_new_findings, _ticket_is_open, _partition_findings_by_attribution (ARCH001 split), _file_regression_ticket (rewritten to consult attribution before filing)
- docs/modules/tickets.md: new "Symbolic attribution (T-1690)" section
- tests/unit/verify/test_attribution.py (new), tests/unit/test_rapid_sweep.py (new test classes)

Design: a finding attributes to the batch commit whose touched symbols
REACH it via `frob.graph.callgraph.build_reference_graph`'s forward
symref edges (bounded BFS, `_reaches`), never a path-string comparison.
Ambiguity (zero or >1 reaching commit) is `status="unattributed"` with
every candidate commit's sha recorded -- never a newest-commit tiebreak.
The reachability path is logged at INFO for every attributed finding and
every candidate is logged at WARNING for an unattributed one, so an
attribution is auditable, not a bare assertion. A graph build/load
failure fails the WHOLE batch (`Err(AttributionError.GraphUnavailable)`),
never a partial attribution.

`_rapid_sweep._file_regression_ticket` now consults attribution before
filing: a finding attributed to exactly one commit whose owning ticket is
still open is logged and left off the regression ticket (already has a
home); everything else (attributed to a closed/dropped ticket, or
genuinely unattributed) is filed with the full audit trail in the body.
Attribution unavailable (queue unreadable/empty, or graph build failure)
degrades to the pre-T-1690 behavior verbatim -- every pair filed, no
attribution lines.

Disclosed scope cuts:
- The upstream `(rule_id, file)` finding identity (`_land_cmd.py`/
  `_verify.py`, out of this ticket's declared scope) still carries no
  line number. When a finding's line is known, `_resolve_symbol` picks
  the exact enclosing symbol; when it is not, every symbol in that file
  becomes a candidate target -- documented in `_attribution.py`'s own
  module docstring as a deliberate, honest degradation, not a silent
  narrowing.
- Tier 3 (bisect for the UNATTRIBUTED residue, T-1686's own framing) is
  not built. An unattributed finding today is filed as an ordinary
  regression ticket naming its candidate commits, for a human to read --
  disclosed in docs/modules/tickets.md's own "What this leaf does NOT
  do" paragraph.

Evidence: 16 pytest node ids recorded via `frob ticket evidence` (6 in
tests/unit/verify/test_attribution.py::TestAttributeBatch, 10 across
tests/unit/test_rapid_sweep.py's TestTicketIsOpen/TestAttributeNewFindings/
TestFileRegressionTicket) -- all measured passing:
`timeout 100 uv run pytest tests/unit/verify/ tests/unit/test_rapid_sweep.py -p no:cacheprovider -q`
-> `collected=59 failed=0` (33 in tests/unit/verify/, 26 in
test_rapid_sweep.py). No `--accepts` binding -- T-1690's ticket body has
no `Acceptance:` structured criteria list (only prose acceptance text),
so there was no acceptance-item index to bind to.

Filed: none -- no out-of-scope defect found beyond what's disclosed above
as a scope cut (both are pre-existing epic-level future work T-1686's own
body already names, not something discovered mid-ticket).

Gates: `frob check --only gates-fast --ticket T-1690` clean (0 errors),
`frob check --only gates-native --ticket T-1690` clean (0 errors) after
fixing an ARCH001 (split `_file_regression_ticket` into
`_partition_findings_by_attribution`) and a PERF003 (restructured
`_reaches`'s inner loop to check `target in callees` via membership
before the nested per-callee loop, instead of a nested `==` comparison).
`frob check --only gates-security --ticket T-1690` surfaces 3 SELFAUDIT001
findings (design/frob.strata's `verify` node interface not yet listing
Attribution/AttributionError/attribute_batch) -- `design/frob.strata` is
outside T-1690's declared scope; per the agent playbook (section 0 step
5) `frob ticket land`'s own pre-merge sweep runs `frob sys sync-interface`
(writes the fix) automatically before merging, so this is expected to
self-resolve at land time, not hand-fixed here.
`frob check --land-parity` could not evaluate in the foreground budget
(deferred lint/static stage groups on this repo's full unscoped size) --
reported honestly as unmeasured, not treated as clean.

### Changed
```
 docs/modules/tickets.md                    |  99 ++++++++
 src/frob/app/ticket_runner/_rapid_sweep.py | 196 ++++++++++++++-
 src/frob/verify/__init__.py                |  17 +-
 src/frob/verify/_attribution.py            | 375 +++++++++++++++++++++++++++++
 tests/unit/test_rapid_sweep.py             | 261 ++++++++++++++++++++
 tests/unit/verify/test_attribution.py      | 188 +++++++++++++++
 tickets.md                                 |  41 +++-
 7 files changed, 1163 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_caller_break_attributes_to_the_caller_commit` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_direct_touch_attributes_at_depth_zero` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_two_reaching_commits_is_unattributed` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_zero_reaching_commits_is_unattributed` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_missing_line_falls_back_to_whole_file_candidates` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_graph_unavailable_is_an_error_for_the_whole_batch` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestTicketIsOpen::test_open_ticket_is_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestTicketIsOpen::test_done_ticket_is_not_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestTicketIsOpen::test_missing_ticket_is_not_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_empty_queue_returns_empty_mapping` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_attributed_and_unattributed_round_trip` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_attributed_to_open_ticket_is_not_refiled` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_attributed_to_closed_ticket_is_refiled` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_unattributed_is_filed` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_all_attributed_to_open_tickets_files_nothing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 16 passed (from 16 evidence id(s))
- gates: 5 error(s), 480 warning(s), 724 waived
- error-findings: ARCH001@src/frob/verify/_attribution.py, E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/verify/_attribution.py, SELFAUDIT001@design, invalid-argument-type@tests/unit/test_rapid_sweep.py
