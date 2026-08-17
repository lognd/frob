---
id: T-2078
title: frob ticket doable auto-drop rewrites terminal tickets then fails the transition,
  destroying Done reports and dirtying the shared root
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_reporting.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
- tests/test_tickets.py
- docs/modules/tickets.md
- tickets/T-2089/
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_reporting.py
  reason: 'T-2078 fix: transition-legality check in drop_ticket, terminal-state filter
    in auto-drop, repro tests'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'T-2078 fix: transition-legality check in drop_ticket, terminal-state filter
    in auto-drop, repro tests'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_reporting.py
  reason: 'T-2078 fix: transition-legality check in drop_ticket, terminal-state filter
    in auto-drop, repro tests'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: 'T-2078 fix: transition-legality check in drop_ticket, terminal-state filter
    in auto-drop, repro tests'
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: tests/unit/test_reporting.py
  reason: 'T-2078: correct test-file scope to the existing TestDropTicket home in
    tests/test_tickets.py; test_reporting.py does not exist'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_tickets.py
  reason: 'T-2078: correct test-file scope to the existing TestDropTicket home in
    tests/test_tickets.py; test_reporting.py does not exist'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-2078: AFFECT001 requires touching drop_ticket''s own doc anchor to describe
    the new pre-check'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-2089/
  reason: 'T-2078: the T-2006 perf follow-up draft this ticket filed lives here; SCOPE001
    flags it as outside scope otherwise'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_tickets.py::TestDropTicket::test_terminal_ticket_transition_refused_before_any_write
- tests/test_tickets.py::TestDropTicket::test_dropped_ticket_transition_refused_before_any_write
- tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition
designated_repro_test: tests/test_tickets.py::TestDropTicket::test_terminal_ticket_transition_refused_before_any_write
acceptance:
- text: given a ticket already in a terminal state (dropped or done) whose regression
    identities no longer reproduce, when frob ticket doable runs its auto-drop pass,
    then that ticket is not selected for dropping and no InvalidTransition error is
    logged -- this test MUST fail against current main
  evidence:
  - tests/test_tickets.py::TestDropTicket::test_terminal_ticket_transition_refused_before_any_write
  - tests/test_tickets.py::TestDropTicket::test_dropped_ticket_transition_refused_before_any_write
  - tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition
- text: given an auto-drop whose transition fails for any reason, when the pass returns,
    then no modification remains in the working tree -- git status --porcelain is
    byte-identical to before the invocation
  evidence:
  - tests/test_tickets.py::TestDropTicket::test_terminal_ticket_transition_refused_before_any_write
  - tests/test_tickets.py::TestDropTicket::test_dropped_ticket_transition_refused_before_any_write
  - tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition
- text: given a done ticket carrying a Done report section, when any auto-drop path
    touches it, then the Done report content is preserved -- verified by content,
    not by exit code
  evidence:
  - tests/test_tickets.py::TestDropTicket::test_terminal_ticket_transition_refused_before_any_write
  - tests/test_tickets.py::TestDropTicket::test_dropped_ticket_transition_refused_before_any_write
  - tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition
threat: null
component: ticket_runner
labels:
- fleet-blocking
- data-loss
anchor: false
anchor_reason: null
land_commit: null
---
## Measured evidence

One `uv run frob ticket doable` on a CLEAN root produced 9 modified files in
the shared root and 9 errors. Verbatim, repeated per ticket:

    WARNING: tickets: T-1998 illegal transition done -> dropped
    ERROR: tickets: T-1998 drop reason recorded but transition failed:
      InvalidTransition: State change not allowed by the state machine
    ERROR: rapid sweep: doable: could not auto-drop resolved regression
      ticket T-1998 (InvalidTransition: State change not allowed by the
      state machine)

Affected: T-1988, T-1998, T-2000, T-2008, T-2022, T-2039, T-2040, T-2052
(9 files, including `tickets/T-1998/done-report.md`). Two illegal shapes
were attempted: `dropped -> dropped` (7 tickets) and `done -> dropped`
(T-1998).

`git status --porcelain` on the root immediately after: 9 entries, all
` M tickets/T-####/...`. No land was in flight.

## The write is DESTRUCTIVE, not merely abandoned

This is the part that makes it critical rather than untidy. `git diff` on
`tickets/T-1998/ticket.md` shows the abandoned write DELETES the ticket's
entire Done report -- a 50+ line block containing its FIX narrative and a
detailed attribution correction with commit shas:

    @@ -57,57 +57,5 @@
    -## Done report
    -
    -FIX: of the 5 (rule, file) identities this ticket named, only ONE was
    -still live at investigation time -- TEST001 on
    -src/frob/app/ticket_runner/_new.py::related_tickets ...
    -ATTRIBUTION CORRECTION (with evidence): this ticket's title and body
    -name T-1977 ... That attribution is WRONG. ...

So the sequence is: rewrite the record for a `dropped` state (dropping the
Done report section), attempt the transition, transition REFUSES, return --
leaving the content-destroying rewrite in the working tree. Anyone who then
runs `git checkout -- tickets/` or commits the root loses the report. I
restored it here with `git checkout HEAD -- <paths>` and verified the
`## Done report` heading is back.

Note this is precisely the failure T-1669's body already describes from an
earlier incident: "the manual refile recipe deletes the block holding the
ticket's evidence and Done report (T-1637) -- it destroyed T-1636's and
recovery needed `git show <commit>~1:tickets.md`". Same destruction, now
reached automatically by a query verb rather than by a manual recipe.

## Why this is NOT already fixed by T-2034

T-2034 (done) fixed `_rapid_sweep.py`'s ledger writes so a write whose
COMMIT fails is discarded, via the shared `_commit_or_discard_ledger_write`
helper. An agent re-read both write paths in that file today
(`_commit_regression_ticket`, `_maybe_drop_resolved_ticket`) and confirmed
both route through it correctly.

This defect is upstream of that: the TRANSITION fails, before any commit is
attempted, so the discard-on-commit-failure guard never runs. The write is
already on disk by then.

## Root cause to confirm (do not assume)

The auto-drop pass selects "resolved regression tickets" whose identities no
longer reproduce, without first checking that the ticket is in a state from
which `dropped` is reachable. Terminal tickets (`dropped`, `done`) are
selected and then refused by the state machine. In the same run, 12 tickets
in a droppable state were auto-dropped successfully (T-2042, T-2043, T-2044,
T-2045, T-2050, T-2051, T-2054, T-2061, T-2062, T-2072 and others), so the
selection is right about "resolved" and wrong only about "droppable".

## DO NOT FIX IT THIS WAY

- **Do not make the state machine permit `dropped -> dropped` or
  `done -> dropped`.** The refusal is correct and is the only reason this was
  visible at all. A ticket that is already terminal must not be re-dropped;
  `done -> dropped` would silently retire completed work. Widening the
  transition table converts a loud, recoverable failure into silent data
  loss.
- **Do not fix only the write-discard half.** Wrapping the write so it is
  rolled back on transition failure removes the dirty root, but leaves the
  pass repeatedly attempting impossible transitions and logging 9 errors per
  invocation on a query verb. Filter terminal tickets out of the candidate
  set as well.
- **Do not silence the log lines.** They are the diagnostic.

## Order of operations

The general rule this violates: compute and validate the transition FIRST,
mutate the record only once it is known to be legal. The repo has paid for
the inverse ordering before -- a pre-land parse guard that ran BEFORE the
rewrite it was meant to cover published three unparseable self-models at
`verified=True`.

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
