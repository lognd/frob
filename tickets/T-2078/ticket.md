---
id: T-2078
title: frob ticket doable auto-drop rewrites terminal tickets then fails the transition,
  destroying Done reports and dirtying the shared root
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given a ticket already in a terminal state (dropped or done) whose regression
    identities no longer reproduce, when frob ticket doable runs its auto-drop pass,
    then that ticket is not selected for dropping and no InvalidTransition error is
    logged -- this test MUST fail against current main
  evidence: []
- text: given an auto-drop whose transition fails for any reason, when the pass returns,
    then no modification remains in the working tree -- git status --porcelain is
    byte-identical to before the invocation
  evidence: []
- text: given a done ticket carrying a Done report section, when any auto-drop path
    touches it, then the Done report content is preserved -- verified by content,
    not by exit code
  evidence: []
threat: null
component: ticket_runner
labels:
- fleet-blocking
- data-loss
anchor: false
anchor_reason: null
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
