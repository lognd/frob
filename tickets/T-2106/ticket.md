---
id: T-2106
title: 'frob ticket doable has no bounded mode: the only way to read the queue is
  a multi-minute full computation, and its argparse error names a --limit flag it
  does not have'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
- src/frob/tickets/_doable.py
- src/frob/app/ticket_runner/_query.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
evidence_scope:
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/ticket_runner/
  reason: narrow from a whole-directory glob (614 scope-closure warnings, locks the
    ticket_runner package away from the fleet) to the two files that actually implement
    doable
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: narrow from a whole-directory glob (614 scope-closure warnings, locks the
    ticket_runner package away from the fleet) to the two files that actually implement
    doable
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: narrow from a whole-directory glob (614 scope-closure warnings, locks the
    ticket_runner package away from the fleet) to the two files that actually implement
    doable
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: the T-2006 sweep re-verification (301s of doable's 736s) lives here; a genuine
    bound means not re-verifying unrelated candidates, which can only be done in this
    module
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: the repro test lives here alongside revalidate_dispatchable_sweep_tickets's
    own existing test suite
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_uncached_recheck_uses_the_doable_budget_not_the_sweep_budget
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

T-2106: bounds `frob ticket doable`'s T-2006 sweep-candidate
re-verification, which the coordinator's own telemetry named as the
single largest line item in doable's cost (301.2s of a measured 736s
run, over 23 sweep-filed candidate tickets / 266 identities).

Root cause (confirmed by reading the code, not guessed): the doable-time
re-verification (`revalidate_dispatchable_sweep_tickets` ->
`_reproducing_identities_cached` -> `_identities_still_reproducing`)
spawns an independent `frob check --budget <N> --json`, and it was
passing `_TRUE_COUNT_BUDGET_S` (300) -- the constant sized for the
DEFERRED POST-LAND SWEEP, not an interactive query. 300 lines up almost
exactly with the measured 301.2s: this call was not "occasionally slow",
it was routinely paying close to its full allotted budget on every
`doable` invocation while any sweep-filed candidate existed.

T-2089's own tree-state-keyed cache (committed as the fix for this exact
cost) does exist and IS correctly wired -- read `_tree_state_key`
directly: it hashes the committed HEAD sha plus `git status --porcelain`.
In a busy multi-agent session HEAD changes on essentially every land, so
under the load the coordinator described (six agents running), the cache
key changes between almost every `doable` call and the cache structurally
cannot hit. Not a "wired to nothing" bug -- a real cache with a
scope that is simply too narrow to help under concurrent load. Filing a
cache-relaxation ticket (widening cache validity across a land that
doesn't touch what's being revalidated) is a separate, larger design
question -- out of this ticket's scope; the fix here targets the
DIRECTLY measured, DIRECTLY actionable cost: the fallback path's own
budget.

Fix: added `_DOABLE_REVALIDATION_BUDGET_S = 20`, threaded into
`_reproducing_identities_cached`'s (uncached) call to
`_identities_still_reproducing`, replacing the 300s `_TRUE_COUNT_BUDGET_S`
default for this one call site. `_true_finding_count_for_identities`
(the deferred sweep's own caller) is untouched -- still 300s, appropriate
for a background pass with no one waiting on it. An unmeasurable-after-
budget result is handled exactly as before (never dropped, never treated
as resolved) -- lowering the budget only changes how LONG doable is
willing to wait for a fresh answer, never what it does with an
inconclusive one.

This is NOT a --limit post-filter (explicitly ruled out in the brief):
no new flag, no filtering after the fact -- the actual expensive
operation is what got bounded, unconditionally, for every `doable` call.

Could not add a `--limit`/`--top` CLI flag as the ticket's title also
names: `src/frob/_cli_parsers/**` (where `doable`'s argparse subparser is
registered) is held by a live cross-worktree lease from T-1382 for
T-2106's entire duration (ScopeLeaseConflict on
`frob ticket scope T-2106 --add
src/frob/_cli_parsers/_ticket/_query.py`, verified directly, retried a
second time near the end of this ticket with the same result). No
CLI-level bound was added in this ticket; the fix instead bounds the
actual measured hotspot unconditionally, which the coordinator's own
brief already anticipated as the correct destination ("a genuine bound
almost certainly means not doing the sweep re-verification at all for a
bounded query") even without a flag to gate it behind.

Measured BEFORE (coordinator-supplied, corrected figure, `/usr/bin/time
-v` on a clean root with six agents running): wall 736s (12:16.05),
user 310.36s, sys 280.16s, 301.2s of which was this ticket's own named
hotspot (`rapid sweep: T-2006: doable-time re-verification of 23
sweep-filed candidate ticket(s) (266 total identit(ies)) took 301.2s`).

Measured AFTER (this ticket's own worktree, same repo, comparable
concurrent load -- other agents still running lands during this
measurement):
  $ time uv run frob ticket doable --json
  real 1m26.492s / user 1m0.231s / sys 0m26.244s
  WARNING: rapid sweep: T-2006: doable-time re-verification of 23
  sweep-filed candidate ticket(s) (268 total identit(ies)) was
  UNMEASURABLE after 80.3s -- leaving them dispatchable, never treating
  unmeasurable as resolved

80.3s ~= budget(20) + the subprocess wrapper's own +60s hard timeout
(`_spawn_true_count_check`'s `timeout=budget + 60`) -- confirms the new
budget is the actual ceiling in effect, not a coincidence. Total doable
wall time: 736s -> 86.5s, roughly 8.5x, and -- more importantly than the
single-run ratio, since load varies -- doable's own re-verification step
now has a hard ~80s ceiling instead of an effectively-unbounded one that
previously ran to the full 300s+ deferred-sweep budget. No branch-
enumeration or lease-listing line showed elevated cost in this run's own
log; nothing else needed reporting per the brief.

Scope corrected/extended from the original 3-file declaration to also
include tests/unit/test_rapid_sweep.py (where the fix's own test lives,
alongside revalidate_dispatchable_sweep_tickets's existing suite) --
src/frob/_cli_parsers/_ticket/_query.py was requested but refused by the
T-1382 lease (see above), so it was never added.

### Changed
```
 tests/unit/test_rapid_sweep.py | 57 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2106/ticket.md       | 21 +++++++++++++++-
 2 files changed, 77 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_uncached_recheck_uses_the_doable_budget_not_the_sweep_budget` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: COV001@src/frob/__main__.py, PRE001@tickets/T-2106, TEST001@src/frob/__main__.py, TICK004@tickets.md
