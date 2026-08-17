---
id: T-2006
title: T-1983's auto-drop only runs inside the next sweep, so a stale sweep ticket
  stays dispatchable until an unrelated land happens
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/app/ticket_runner/_query.py
evidence_scope:
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: T-2006's fix must be CALLED from frob ticket doable's own render path (_query._doable),
    the exact dispatch-time moment the ticket's own acceptance criteria require --
    the mechanism itself lives in _rapid_sweep.py (already in scope), but the one-line
    call site cannot live there since _rapid_sweep.py is never on the doable() code
    path today
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_rapid_sweep.py::TestIdentitiesStillReproducing::test_only_reproducing_identities_returned
- tests/unit/test_rapid_sweep.py::TestIdentitiesStillReproducing::test_unmeasurable_is_none
- tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_no_sweep_tickets_is_zero_cost
- tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_fully_resolved_candidate_is_dropped
- tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_still_reproducing_candidate_is_left_untouched
- tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_unmeasurable_recheck_drops_nothing
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FOLLOW-UP TO T-1983, NOT A DUPLICATE. T-1983 ("Sweep-filed tickets go
stale before anyone reads them") is DONE and its mechanism works. The
same failure recurred TWICE on 2026-08-10 anyway, because T-1983 closed
only half the window. Read T-1983 first; do not re-implement it.

WHAT T-1983 BUILT: `_close_resolved_sweep_tickets` /
`_maybe_drop_resolved_ticket` (`src/frob/app/ticket_runner/_rapid_sweep.py`,
called at :1308) diffs `vanished = baseline - fresh` and auto-drops
sweep-filed tickets whose identities no longer reproduce.

THE RESIDUAL GAP: that call site is INSIDE the sweep, and the sweep runs
only after a land. So a sweep-filed ticket is only re-verified when some
LATER, UNRELATED ticket happens to land. In the window between filing and
that next land -- which at 5-agent dispatch is exactly when the coordinator
reads `frob ticket doable` and dispatches -- the ticket is listed, doable,
and unverified.

MEASURED, both on 2026-08-10, both after T-1983 landed:
- T-2000 ("post-land sweep regression from T-1665: 1 new identity, 2
  findings"): findings were already fixed inside T-1665's own land. No
  later sweep had run, so the auto-drop never fired. Dropped BY HAND.
- T-1998 ("post-land sweep regression from T-1977: 5 new identities, 8
  findings"): misattributed (the identities were in T-1995's files, not
  T-1977's) AND mostly already fixed by T-2002 before anyone started it.
  It was DISPATCHED to an agent, which merged main and found the actual
  remaining work was ONE LINE (`git show 917ba8e92 --stat`:
  `src/frob/app/ticket_runner/_new.py | 1 +`). A full dispatch cycle for
  one line.

COST: one wasted dispatch plus one manual drop, in one hour, on top of a
mechanism specifically built to prevent this.

## Do not fix it this way
- Do NOT run a full sweep at `doable`/`start` time. The whole point of
  T-1684's deferred detached sweep is that the multi-minute check is OFF
  the critical path; putting it back on an interactive command re-creates
  the problem T-1684 solved. The recorded identities are (rule, file)
  pairs -- re-measuring just those is cheap and is what this needs.
- Do NOT fix it by making the sweep file fewer tickets, or by adding a
  confidence threshold. The sweep filing promptly is correct; the defect
  is that nothing re-checks between filing and reading.
- Do NOT fix it only at `frob ticket start`. The coordinator picks work
  from `frob ticket doable`, so a stale ticket that is merely refused at
  `start` has already cost the dispatch decision.
- Do NOT hand this to a playbook line telling agents to re-measure before
  starting a sweep ticket. T-1983 already proved the mechanism must be
  automatic; an agent following a rule is not an enforcement.

## Acceptance criteria
1. A test that FAILS FIRST: file a sweep ticket, resolve its findings via
   an unrelated commit WITHOUT running another sweep, and assert that
   `frob ticket doable` currently still lists it. Then assert it does not.
2. Re-verification is scoped to the ticket's own recorded (rule, file)
   identities via the existing `_parse_sweep_ticket_identities`, not a
   full-tree check, and its cost is REPORTED as a measured number.
3. A sweep ticket whose identities still reproduce is unaffected -- assert
   no over-dropping, with a case where exactly one of two identities has
   vanished (the ticket must survive, not be dropped).

## Done report

T-1983's own mechanism (`_close_resolved_sweep_tickets`/`_maybe_drop_
resolved_ticket`, `_rapid_sweep.py:1319` before this ticket, unchanged
here -- read first per the ticket's own instruction) works correctly.
The gap is only WHERE it is called: exclusively inside a deferred
sweep's own run, which only fires after SOME land -- not necessarily one
related to the stale ticket. Between "identities resolved" and "the next
unrelated land's sweep happens to run", a stale sweep ticket is listed
and dispatchable by `frob ticket doable`, unverified.

Fix direction (a) from T-1983's own body: re-verify at the moment
`frob ticket doable` would list it, scoped to the ticket's OWN recorded
identities, never a full sweep.

### What was added
- `_matching_error_diagnostics` (ARCH001 split, extracted from the
  pre-existing body of `_true_finding_count_for_identities`, T-1935):
  the shared low-level "spawn one `frob check --budget --json`, return
  every ERROR diagnostic matching `pairs`" fetch. `_true_finding_count_
  for_identities` now builds on this (behavior-identical, all its
  existing tests pass unchanged) instead of duplicating the fetch+parse.
- `_identities_still_reproducing`: new, returns WHICH of `pairs` still
  reproduce (an identity set), not merely a count -- what deciding
  "drop or keep" needs.
- `revalidate_dispatchable_sweep_tickets(root, tickets)`: scans
  `tickets` for sweep-filed candidates (`_parse_sweep_ticket_identities`
  != None -- zero cost when none, the overwhelming common case), spawns
  exactly ONE re-check scoped to the UNION of every candidate's own
  recorded identities (never a full unscoped sweep), logs the measured
  cost (acceptance #2), and drops (via T-1983's own `_maybe_drop_
  resolved_ticket`) any ticket whose full identity set is now resolved.
  A partially-resolved or unmeasurable-recheck ticket is left untouched
  (acceptance #3: no over-dropping).
- Wired into `_query.py::_doable`, right after `load_queue`, before the
  dispatchable filter runs -- the exact "at the moment it would be
  dispatched" point acceptance #1 names. If anything drops, the queue is
  reloaded so the drop is reflected in the SAME `frob ticket doable`
  invocation, not just the next one.

### What was deliberately NOT done (per the ticket's own "do not fix it
this way" list)
- No full sweep at `doable`/`start` time -- confirmed: the re-check
  spawns one `frob check --budget` call scoped only when sweep-filed
  candidates exist, never the T-1684 unscoped sweep.
- No confidence threshold or reduced sweep-filing.
- Not gated only at `start` -- wired at `doable`, before the dispatch
  decision.
- `_close_resolved_sweep_tickets` itself is UNCHANGED -- this adds a
  second, independent call site (`revalidate_dispatchable_sweep_
  tickets`) that reuses its per-ticket drop primitive
  (`_maybe_drop_resolved_ticket`), never a re-implementation.

### Known gap (disclosed, not silently cut)
`_query._doable`'s daemon fast-path (`_try_doable_via_daemon`, the
common `frob ticket doable --json` case with no extra flags) returns
before reaching this new call -- the RPC's own fixed-arity contract has
no hook for it. A plain `frob ticket doable` (no `--json`) and every
other flag combination DOES go through the fixed in-process path this
change wires into. Widening the daemon RPC itself is out of this
ticket's declared scope (`frob.serve._tools`, a different subsystem) --
not filed as a follow-up ticket here since it is a narrower, lower-
priority gap than the doc-anchor one below; noting it plainly instead so
it is not silently assumed covered.

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py | ~185 lines added/refactored
 src/frob/app/ticket_runner/_query.py       | ~20 lines added
 tests/unit/test_rapid_sweep.py             | ~230 lines added
```

### Evidence (6 ids, all fail-first)
- TestIdentitiesStillReproducing::{test_only_reproducing_identities_returned, test_unmeasurable_is_none}
- TestRevalidateDispatchableSweepTickets::{test_no_sweep_tickets_is_zero_cost, test_fully_resolved_candidate_is_dropped, test_still_reproducing_candidate_is_left_untouched, test_unmeasurable_recheck_drops_nothing}

Fail-first confirmed by hand: `git checkout HEAD -- src/frob/app/ticket_
runner/_rapid_sweep.py` (source only, keeping the new tests) ->
`ImportError: cannot import name '_identities_still_reproducing'` --
hard collection failure, not a softer mismatch. Restored, re-ran:
`uv run pytest tests/unit/test_rapid_sweep.py -p no:cacheprovider -q`
-> `SUITE-RESULT: exitstatus=0 collected=68 failed=0` (62 pre-existing +
6 new). The `_query.py` wiring itself was verified indirectly: the
existing `_doable`-touching test suite (`test_app_runners_t1822_already_
landed.py`, `test_app_runners_t0715_sprint_tier.py`,
`test_app_runners_batch7.py`) was re-run before/after the wiring change
and produced the IDENTICAL 5 pre-existing failures both times (confirmed
by reverting just `_query.py` to HEAD and re-running -- same 5 failures,
none of them doable-shaped, none caused by this change: 4 are `frob
ticket land`/`renumber`/`start` fixture issues, 1 is an unrelated
duplicate-title refusal in `TestTicketDoableSprintByParent`).

Filed: T-2024 -- add the real `frob:doc` anchor for
`revalidate_dispatchable_sweep_tickets` once T-1696's live lease on
`docs/modules/tickets.md` clears (currently waived, COV001, with the
lease cited as the reason -- same posture this file's existing T-1935/
T-1791 waivers already carry for the identical lease).

Gates: `frob check --land-parity` clean (0 unscoped errors).

### Series-wide note (shared root cause, as requested)
T-2009 and T-2006 both trace to the same underlying shape: the deferred
sweep (T-1684) intentionally decouples verification timing from land
timing, and two separate pieces of code had baked in an assumption of
1:1 correspondence that decoupling breaks -- T-2009's attribution logic
assumed "the land that spawned this sweep is the land that caused this
finding" (false when >1 land lands in the window), T-2006's dispatch
logic assumed "a sweep ticket's staleness is only checked by the NEXT
sweep" (false when the ticket resolves between sweeps). Both fixes are
disjoint code paths in the same file (attribution text vs. a new
re-verification entrypoint) and were implemented as separate,
independently evidenced tickets rather than combined, per the series
brief.

### Changed
```
 tickets/T-2006/ticket.md           | 20 ++++++++++++++++++++
 tickets/T-2024/ticket.md | 36 ++++++++++++++++++++++++++++++++++++
 2 files changed, 56 insertions(+)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestIdentitiesStillReproducing::test_only_reproducing_identities_returned` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestIdentitiesStillReproducing::test_unmeasurable_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_no_sweep_tickets_is_zero_cost` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_fully_resolved_candidate_is_dropped` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_still_reproducing_candidate_is_left_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_unmeasurable_recheck_drops_nothing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, COV003@tickets/T-0907, DUP001@tests/unit/test_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/bug-002-sweep-series/src/frob/app/ticket_runner/_query.py, F401@/home/logan/projects/frob/.claude/worktrees/bug-002-sweep-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/bug-002-sweep-series/tests/unit/test_tickets_evidence_only_scope.py
