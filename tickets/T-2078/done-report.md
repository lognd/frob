## Done report

FIX (two halves, both required per the ticket's DO-NOT-FIX-IT-THIS-WAY
section):

1. `drop_ticket` (src/frob/tickets/_reporting.py) now validates the
   transition's legality BEFORE writing anything. A new pure helper,
   `_is_transition_legal(current, to)`, checks the same
   `frob.tickets._TRANSITIONS` state machine table `transition()` itself
   enforces. A ticket already terminal (`done`/`dropped`) is refused with
   `Err(InvalidTransition)` and ZERO writes -- the drop-reason body splice
   (which is what destroyed T-1998's Done report in the incident) never
   runs at all for an illegal transition. The state machine itself is
   UNCHANGED: `dropped -> dropped` and `done -> dropped` both stay
   illegal, exactly as the ticket required.

2. `_maybe_drop_resolved_ticket` (src/frob/app/ticket_runner/_rapid_sweep.py),
   the shared per-ticket drop decision both `_close_resolved_sweep_tickets`
   (T-1983) and `revalidate_dispatchable_sweep_tickets` (T-2006, called
   directly from `frob ticket doable`'s render path against the FULL
   candidate set) route through, now also checks `_is_transition_legal`
   before calling `drop_ticket` at all. `_close_resolved_sweep_tickets`
   already filtered to QUEUED/PLANNED before calling here, but
   `revalidate_dispatchable_sweep_tickets` never did -- this closes that
   gap at the shared decision point instead of duplicating the state
   filter per call site, and avoids the InvalidTransition log noise
   entirely for a ticket that was never a real candidate.

Both halves were needed, confirmed by the repro tests: filtering alone
(half 2) would still leave `drop_ticket` writing destructively before
validating for any OTHER caller; the legality check alone (half 1) would
still let `doable` attempt (and log) a doomed transition on every
invocation for an already-terminal sweep ticket.

Evidence, PRE-LAND REPRO TECHNIQUE (playbook 7b): the repro tests were
committed ALONE first (1422aee48), confirmed FAILED_AT_PARENT via
`frob ticket evidence T-2078 --check-repro <node-id> --base-ref 1422aee48`
(measured: genuinely fails), THEN the fix was committed separately
(4392f00aa) and confirmed passing. `--designate-repro` was bound against
that test-only sha and ACCEPTED (FAILED_AT_PARENT, a real repro, not
confirmatory-only).

Acceptance criteria, all bound and verified BY CONTENT:
  [0] tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition
      -- a DROPPED sweep ticket whose identities resolve is not
      re-selected by `revalidate_dispatchable_sweep_tickets`, and
      `caplog.text` contains neither "illegal transition" nor
      "InvalidTransition".
  [1] tests/test_tickets.py::TestDropTicket::test_terminal_ticket_transition_refused_before_any_write
      and ::test_dropped_ticket_transition_refused_before_any_write --
      `path.read_bytes()` before and after a refused `drop_ticket` call
      on a DONE and a DROPPED ticket are byte-identical (not merely
      content-equivalent).
  [2] test_terminal_ticket_transition_refused_before_any_write also
      asserts `"## Done report" in reloaded_text` and the FIX narrative
      text survives verbatim after the refused call.

Measured: `uv run pytest tests/test_tickets.py tests/unit/test_rapid_sweep.py`
-- 248 passed (one test,
`TestDeferredSweepClosesResolvedRegressions::test_resolved_finding_is_dropped_by_the_next_sweep`,
failed once under xdist parallel ordering and passed both standalone and
in a full re-run immediately after -- pre-existing test-isolation flake,
unrelated to this ticket's files, not touched by this diff).

Gates: `frob check --ticket T-2078 --only test` clean (0 errors);
`--only archgate --only coverage --only sys` clean after fixing two
self-inflicted issues found along the way (an AFFECT001 from the new
helper's directive block displacing `drop_ticket`'s own frob:ticket/
frob:doc comments -- fixed by reordering, and the doc anchor itself
needed a one-paragraph update, both included in this ticket's diff);
`frob check --land-parity` clean (0 unscoped errors, after fixing one
E501 the unscoped ruff pass caught); `git diff main --diff-filter=D
--stat` empty (no unintended deletions).

Investigated separately, kept out of this ticket's own diff per the
brief's explicit instruction: the same run's `rapid sweep: T-2006:
doable-time re-verification ... took 207.5s` line. The fix itself
belongs entirely inside T-2089's own scope, filed as a
standalone ticket rather than folded into this one.

Filed: T-2089 (an uncached full-check spawn in the doable-time sweep-candidate revalidation path, 207.5s measured; kept as a standalone follow-up per this ticket's own brief).

Gates: frob check --ticket T-2078 --only test / --only archgate --only
coverage --only sys clean; frob check --land-parity clean; no waivers
needed for this ticket's own diff.

### Changed
```
 docs/modules/tickets.md                    |   8 +++
 src/frob/app/ticket_runner/_rapid_sweep.py |  19 ++++-
 src/frob/tickets/_reporting.py             |  37 ++++++++++
 tests/test_tickets.py                      |  62 +++++++++++++++++
 tests/unit/test_rapid_sweep.py             |  85 +++++++++++++++++++++++
 tickets/T-2078/done-report.md              | 107 +++++++++++++++++++++++++++++
 tickets/T-2078/ticket.md                   |  81 ++++++++++++++++++++--
 tickets/T-2089/ticket.md         |  90 ++++++++++++++++++++++++
 8 files changed, 482 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestDropTicket::test_terminal_ticket_transition_refused_before_any_write` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDropTicket::test_dropped_ticket_transition_refused_before_any_write` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: none (measured, zero errors)
