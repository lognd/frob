## Done report

Two independent defects, both measured directly against T-3064's incident.

(1) BlockerOpenAtClose: `_open_blockers_at_close` (src/frob/app/ticket_runner/_close_cmd.py)
runs inside `_close()`, right after the T-1648 remainder-disclosure check and
before the close-guard computation. It looks at `fresh_ticket.blocked_by`,
resolves each id against a freshly-loaded queue, and collects the ones whose
state is NOT done/dropped. Any non-empty result refuses the close
(`sys.exit(1)`) with a hint pointing at `frob ticket unblock`. A blocker id
that has itself reached done/dropped is never collected -- the check is on
the blocker's CURRENT state, not the mere presence of a `blocked_by` entry,
so a ticket whose blockers all resolved closes exactly as it did before this
change (must-stay-quiet fixtures: test_terminal_blocker_never_refuses,
test_dropped_blocker_never_refuses). Deliberately placed in the CLI layer
(`_close_cmd.py`), not `frob.tickets._evidence.transition`'s guard chain --
`_evidence.py` is leased by T-3038 for the duration of this ticket, and the
guard's own shape (load queue, check state, refuse-with-a-hint) matches the
sibling checks (`_undisclosed_remainder_reason`) already living at this
layer rather than the injected-boolean pattern `transition()` uses for
checks that need `frob.gates`/`frob.testing`.

(2) reopen_ticket (src/frob/tickets/_reporting.py), wired as `frob ticket
reopen <id> --reason TEXT`: the explicit, reason-carrying, audited escape
hatch T-3087 asked for, in the exact posture `frob ticket fail` already has.
It refuses on a blank reason (ReopenReasonMissing) and on any non-DONE
starting state (ReopenRequiresDone), appends a dated line under a new '##
Reopen log' body section (added to `_STRUCTURAL_HEADINGS_AFTER_DONE_REPORT`
in src/frob/tickets/_models.py, alongside Failure log/Drop reason, so the
Done-report-section scanner keeps treating it as a real structural
boundary), and writes state=QUEUED directly via `write_ticket`.

INVARIANTS CHECKED: this does NOT add a DONE -> QUEUED edge to
`frob.tickets._TRANSITIONS` (still `TicketState.DONE: frozenset()`), so the
generic `transition(root, id, TicketState.QUEUED)` remains categorically
refused for a done ticket from every OTHER call site -- reopen_ticket's own
narrow state check and direct write are the only path in. Every other
terminal-state consumer (archive's done/dropped sweep, milestone rollups,
`doable`'s closure, `_open_descendant_ids`) reads `ticket.state` as it
stands when it runs; after a real reopen that state is genuinely QUEUED
again, so there is no split-brain "done but also reopened" value for any of
them to misread, and none of their own code changed.

T-3064 DISPOSITION: left closed, not reopened. T-3086 ("Break the 182-node
import cycle (redo)") already exists, queued, and already re-declares the
same scope T-3064 was supposed to touch. Reopening T-3064 now would create
two active tickets racing the same scope/lease -- worse than the status quo,
not a fix. Per the ticket's own acceptance ("either reopened... or
explicitly left closed with a note pointing at T-3086"), a dated note is
being added to T-3064's body under '## Reopen log' explaining the decision
(via `frob ticket body --append`, a separate ledger action after this
land, since T-3064 is not in this ticket's scope).

EMPTY-CODE-DIFF WARN: NOT implemented. The brief marks it optional ("if you
implement..."), and it needs a `frob check`-time diff-family scan
(distinguishing a real empty-diff BUG/FEATURE close from a legitimate
docs/epic/no_scope_declared one) that belongs in `frob.gates`, a dependency
`frob.tickets` deliberately stays free of (see `_done_transition_guard`'s
own docstring on why covers_scope/mutation_evidence/etc. are all injected,
never computed, in this package) -- doing it properly is its own ticket, not
a tack-on here. Filed as a follow-up.

Filed: T-3090 (empty-code-diff-on-close WARN, deferred per the above)

COORDINATOR MEASUREMENT (post-brief, folded in here): a full sweep of the
active ledger (266 tickets, 18 with a `blocked_by`) for the T-3064 shape
found the real live-instance count is ZERO -- T-3064 was the only genuine
occurrence, and it self-resolved when T-3066 landed. Three raw hits
(T-1600/T-1604 blocked by T-1599, T-2361 blocked by T-2360) were false
positives: their blockers are `state: done` but archived out of `tickets/`,
so an active-only scan cannot distinguish "blocker archived done" from
"blocker id does not exist." `_open_blockers_at_close` was already immune to
this: `_close()` resolves blockers through `load_queue`, which merges
active+archive (`_load_merged`) rather than an active-only lookup, and any
blocker id absent from that merged view is treated as UNKNOWN (skipped, not
counted as open) -- the T-1664 doctrine that UNRESOLVED is a third state,
never an error. Added
test_archived_terminal_blocker_resolves_via_load_queue, which drives a real
`archive()` move (not a mock) to prove this against the actual merged-load
path, not just `_open_blockers_at_close`'s own dict handling. No code
change was needed for this finding -- the guard already had the right
resolution source; the finding is now recorded as a fixture so it stays
proven.

### Changed
```
 docs/modules/tickets.md                    |  20 ++++++
 src/frob/_cli_parsers/_ticket/_closeout.py |  18 +++++
 src/frob/app/ticket_runner/__init__.py     |   4 ++
 src/frob/app/ticket_runner/_close_cmd.py   |  99 +++++++++++++++++++++++++
 src/frob/tickets/__init__.py               |   2 +
 src/frob/tickets/_models.py                |  30 +++++++-
 src/frob/tickets/_reporting.py             |  80 +++++++++++++++++++++
 tests/unit/test_close_blocked_by_guard.py  |  91 +++++++++++++++++++++++
 tests/unit/test_reopen_ticket.py           | 112 +++++++++++++++++++++++++++++
 tickets/T-3087/ticket.md                   |  70 +++++++++++++++++-
 tickets/T-3092/ticket.md         |  36 ++++++++++
 11 files changed, 560 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose::test_open_blocker_names_the_open_ticket_not_the_terminal_one` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose::test_terminal_blocker_never_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose::test_dropped_blocker_never_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose::test_no_blocked_by_returns_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose::test_unresolvable_blocker_id_is_ignored` (pytest node id, verified passing when recorded)
- `tests/unit/test_reopen_ticket.py::TestReopenTicket::test_reopen_requires_done` (pytest node id, verified passing when recorded)
- `tests/unit/test_reopen_ticket.py::TestReopenTicket::test_reopen_requires_reason` (pytest node id, verified passing when recorded)
- `tests/unit/test_reopen_ticket.py::TestReopenTicket::test_reopen_appends_dated_entry_and_requeues` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose::test_archived_terminal_blocker_resolves_via_load_queue` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 85 error(s), 1058 warning(s), 862 waived
- error-findings: AFFECT001@src/frob/tickets/_models.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3080/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3088/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/app/ticket_runner/_close_cmd.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@src/frob/tickets/_reporting.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/app/ticket_runner/_close_cmd.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@src/frob/tickets/_reporting.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, DUP001@tests/unit/test_close_blocked_by_guard.py, DUP001@tests/unit/test_reopen_ticket.py, E501@/home/logan/projects/frob/.claude/worktrees/series-bg/src/frob/tickets/_models.py, E501@/home/logan/projects/frob/.claude/worktrees/series-bg/src/frob/tickets/_reporting.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bg/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3087, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py, invalid-argument-type@tests/unit/test_close_blocked_by_guard.py
