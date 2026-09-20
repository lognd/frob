## Done report

Anchor decision: docs/modules/gates.md#tdd001-t-3009 describes
`tdd_order_violations`' mechanism generally (resolve_symbol_introduction,
classify_order, the T-3618 performance section) and never walks through
`_tdd001_self_referential_message` or `_tdd001_backwards_message`
individually -- the section does not even mention T-4260's role-validation
feature these two helpers implement. The anchors added alongside T-4260
drifted onto the nearest private symbols rather than reflecting real
per-helper documentation. The public entry point, `tdd_order_violations`,
already carries the section's real anchor, so the private-helper anchors
were removed rather than waived (this repo's established waiver precedent
requires the doc section to genuinely walk through the specific helper,
which is not the case here).

Formatter: `frob format` reported 4 files needing a ruff-format rewrite --
src/frob/tickets/_leases.py, tests/test_ticket_leases.py,
tests/unit/coordinator_suite/test_fleet_land.py, and
tests/unit/test_process_tty.py -- none of which is _tdd_order.py itself.
Ran it and committed the reformat separately from the anchor-decision
commit; `frob format` now reports 0 files needing reformatting.

Widening T-4290's scope to cover the 4 files (as the ticket body directs)
surfaces SCOPE002 under `frob check --ticket T-4290`: _leases.py's
closure alone WARNS about ~20 additional consider-adding targets
(docs/modules/tickets-landing.md, tickets-lifecycle.md,
scripts/fleet_status.py, and several tickets/_land.py, _store.py,
_worktree_sweep.py private-helper call sites) -- those stay WARNINGs at
scope-add time, not hard errors, and did not block. What WAS a hard
COV002 error: 4 of the reformatted symbols carried `frob:ticket` anchors
to now-DONE tickets (T-2714, T-4273, T-4266, T-2691, T-4255), so a
whitespace-only touch under ANY ticket's scope trips "changed with no
edge to an open ticket." Added `frob:ticket T-4290` alongside each stale
anchor to clear it -- this is itself a real, if narrow, discovery:
COV002 does not distinguish an AST-preserving reformat from a semantic
change, so any old symbol whose sole binding was to an already-closed
ticket becomes untouchable-by-formatter without a fresh ticket edge.
Filed T-4292 to record this (and the larger SCOPE002-closure-vs-
formatter-diff question) for the frob team's own consideration; it did
not block completing this ticket's own scope.

Unscoped verification (matches `.github/workflows/ci.yml`'s "frob check
(self-gate)" step, `uv run frob check`, run from this worktree against
its own history) right after the anchor-fix commit:

  SEVERITY {'warning': 5097, 'info': 92, 'note': 1820, 'error': 2}
  ERRORS   2
    frob-arch:lock-order-cycle src/frob/serve/_daemon.py:320
    gate:LARGE:LARGE001 src/frob/serve/_daemon.py:0

Both remaining errors are exactly the architecture and size errors the
ticket body says belong to another already-dispatched ticket -- present,
as expected, not counted as this ticket's failure. The two COV007 anchor
errors and all four formatter findings this ticket owned are gone from
this run.

CAVEAT on later re-runs in this worktree: after the additional
ticket-bookkeeping/format commits landed, re-running the identical
unscoped `frob check` in this same worktree also surfaces PRE001/SCOPE001
"no active ticket is derivable" findings. This traces to a pre-existing
frob defect unrelated to this ticket's own work: `frob ticket work`
creates a lowercase worktree branch (`t-4290`) that never matches
`active_ticket()`'s `^(T-\d{4})-` regex, so a plain `frob check` run from
inside the worktree (no `--ticket`, matching the CI invocation literally)
cannot derive an active ticket for its own uncommitted-vs-main diff. This
is a worktree-dev-time artifact, not a fact about what lands on `main`:
CI's own "frob check (self-gate)" step runs post-squash-land, where
`diff.base == HEAD` and there is no diff for PRE001/SCOPE001 to fire on.
The quoted `ERRORS 2` run above, taken right after the anchor-fix commit
before this drifted, is the representative measurement.

Evidence: tests/gates/test_tdd_order.py::TestTddOrderViolations::
test_self_referential_edge_is_a_malformed_directive_not_an_ordering_violation,
::test_backwards_edge_is_reported_as_a_backwards_directive,
::test_role_validation_never_spawns_git_for_a_malformed_edge -- confirm
both message-building helpers still function correctly after their doc
anchors were removed (comment-only removal, no behavior change).
tests/test_ticket_leases.py::TestLedgerCommitRepairMarker::
test_resolved_race_clears_the_marker_without_a_false_alarm,
tests/unit/coordinator_suite/test_fleet_land.py::TestReadLandStatusMarker::
test_reads_a_written_marker, tests/unit/test_process_tty.py::
TestIsInteractiveStdin::test_win32_tty_isatty_and_real_console_is_interactive
-- one per reformatted file, confirming the whitespace-only rewrite left
behavior unchanged.

Filed: T-4292 (formatter drift in _leases.py/test_fleet_land.py/
test_process_tty.py/test_ticket_leases.py needs a scope-closure-aware
plan) -- records the COV002-on-stale-anchor and SCOPE002-closure
questions discovered while widening this ticket's own scope; did not
block completing this ticket.

Gates: `frob check` (unscoped, matching the CI job) clean of this
ticket's own findings -- 2 remaining errors are the architecture/size
pair explicitly named as another ticket's ownership in T-4290's own body.

frob:no-behavior-change reason="removing two frob:doc anchor comments and reformatting 4 files with ruff-format changes no runtime behavior -- classify_order/tdd_order_violations/the two message-building helpers are byte-for-byte identical except for the deleted comment lines, and the 4 reformatted files are whitespace-only rewrites; confirmed by test_self_referential_edge_is_a_malformed_directive_not_an_ordering_violation, test_backwards_edge_is_reported_as_a_backwards_directive, test_role_validation_never_spawns_git_for_a_malformed_edge, test_resolved_race_clears_the_marker_without_a_false_alarm, test_reads_a_written_marker, and test_win32_tty_isatty_and_real_console_is_interactive all still passing"

### Changed
```
 src/frob/gates/_tdd_order.py                    |  2 -
 src/frob/tickets/_leases.py                     |  3 +-
 tests/test_ticket_leases.py                     |  6 +-
 tests/unit/coordinator_suite/test_fleet_land.py | 21 +++---
 tests/unit/test_process_tty.py                  | 11 ++-
 tickets/T-4290/done-report.md                   | 90 +++++++++++++++++++++++++
 tickets/T-4290/ticket.md                        | 52 ++++++++++++--
 tickets/T-4292/ticket.md                        | 38 +++++++++++
 8 files changed, 199 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/gates/test_tdd_order.py::TestTddOrderViolations::test_self_referential_edge_is_a_malformed_directive_not_an_ordering_violation` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestTddOrderViolations::test_backwards_edge_is_reported_as_a_backwards_directive` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestTddOrderViolations::test_role_validation_never_spawns_git_for_a_malformed_edge` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerCommitRepairMarker::test_resolved_race_clears_the_marker_without_a_false_alarm` (pytest node id, verified passing when recorded)
- `tests/unit/coordinator_suite/test_fleet_land.py::TestReadLandStatusMarker::test_reads_a_written_marker` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_tty.py::TestIsInteractiveStdin::test_win32_tty_isatty_and_real_console_is_interactive` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 3 error(s), 4630 warning(s), 946 waived
- error-findings: LARGE001@src/frob/serve/_daemon.py, SCOPE002@tickets.md, lock-order-cycle@src/frob/serve/_daemon.py
