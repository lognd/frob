---
id: T-2571
title: 'Post-land sweep files identical (rule,file) identities as new regressions
  across unrelated lands: baseline recurrence/phantom-path bug'
state: in-progress
kind: bug
origin: agent
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets-verify-sweep.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given the rolling baseline .frob/rapid-sweep-baseline.json is written on sweep
    N with a fresh finding set F, when sweep N+1 runs against an unrelated single-file
    land and measures the same set F again, then no identity in F appears in sweep
    N+1's new_findings diff (or, if it does, the log states explicitly why the prior
    write did not survive).
  evidence: []
- text: Given a (rule, file) identity whose file does not exist in the tree being
    checked (e.g. a deleted monofile, or a ticket id that lives at tickets/archive/<id>
    rather than tickets/<id>), when the sweep computes its fresh finding set, then
    that identity is either not produced at all or is flagged distinctly as referencing
    a non-current path, never silently filed as an ordinary new regression.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684, `frob.app.ticket_runner._rapid_sweep`)
is producing sweep-regression tickets at a very high false-positive rate. Four
consecutive queued tickets were triaged this session -- T-2381 (27 identities),
T-2474 (39), T-2525 (38), T-2560 (38) -- and ALL FOUR were measured 100% false
positive and dropped. Combined with two prior triage sessions (T-2538: 5/5
pre-existing; T-2483: 1/2 pre-existing; an earlier one: 5/6 pre-existing), the
measured true-new-regression rate across everything triaged to date is
approximately 4 genuinely-new identities out of 4+13+38+39+38+27 = roughly
159 measured identities (~2.5%), i.e. the sweep is wrong about 97% of the time
it accuses a specific land.

Method used (reusable): resolve the land commit named in the ticket, confirm
it `is_ancestor_of main`, then `git show --stat` it to get its REAL touched-file
set, and check whether ANY flagged (rule, file) identity names one of those
files. In this session's four tickets, the land commits were:

- T-2474/T-2458: edf1786a -- touched ONLY `tickets/T-2472/ticket.md` (a
  single-ticket-file `chore(tickets): file T-2472` commit). None of the 39
  flagged files overlap.
- T-2525/T-2503: 75f62ad7 -- touched ONLY `tickets/T-2523/ticket.md`. None of
  the 38 flagged files overlap.
- T-2560/T-2552: c1328b82 -- touched CHANGELOG.md, changelog.d/T-2552.md,
  docs/modules/arch.md, rapid-debt.jsonl, src/frob/arch/_mayraise.py,
  tests/unit/test_arch.py, tickets/T-2543, tickets/T-2552. None of the 38
  flagged files overlap.
- T-2381/T-2356: e2ed6048 -- the ledger-v2 cutover (deleted tickets.md /
  tickets-archive.md, touched src/frob/gates/_tickets_gate.py,
  tests/test_tickets_migration.py, docs/design/ledger-v2.md,
  tickets/T-2356). None of the 27 flagged files overlap either -- including
  `TICK003`/`TICK004 tickets.md`, which is a phantom finding: `tickets.md`
  was DELETED by this same land and does not exist anywhere on main today.

Two concrete defect classes were found, both worth root-causing separately
from "which specific ticket is right":

1. **Phantom findings against paths that no longer exist.** `TICK003`/
   `TICK004 tickets.md` fired in three of the four tickets (T-2381, T-2474,
   T-2525) after `tickets.md` had already been deleted by the T-2356 ledger-v2
   land. Whatever check produces this identity is either reading a stale
   cache, or the sweep's "fresh" measurement itself is not reading the
   current tree.

2. **The same identity set recurs as "new" across consecutive, unrelated
   sweeps.** `COV003 tickets/T-1205`, `T-1235`, `T-1397`, `T-1526`, `T-1688`
   appear in T-2381, T-2474, AND T-2525 (three different sweeps, three
   different unrelated lands); `T-2344`/`T-2348` join starting at T-2474 and
   persist into T-2525/T-2560; `T-2365` joins at T-2525 and persists into
   T-2560. `TICK003`/`TICK004 tickets.md`, `SELFAUDIT001 design`,
   `SEC110 tests/test_release.py`, `WIRE003 docs/modules/cli.md`,
   `DOC011 docs/design/gate-semantics-classification.md`, `PERF003
   src/frob/gates/_debt_deprecated.py`, `PERF004
   src/frob/app/ticket_runner/_new.py`, `RENDER001 src/frob/release/_cli.py`,
   `ARCH103 src/frob/release/_cli.py` recur in EVERY one of the four tickets.
   If the rolling baseline (`.frob/rapid-sweep-baseline.json`,
   `_write_baseline`/`_read_baseline` in `_rapid_sweep.py`) correctly
   recorded the fresh set on every sweep as documented, an identity present
   in sweep N's fresh set should be present in sweep N's baseline and
   therefore ABSENT from sweep N+1's `new_findings = fresh - baseline` diff.
   Seeing the identical identity set survive three-plus consecutive sweeps
   as "new" each time means EITHER the baseline write is not surviving to
   the next sweep's read (a persistence/race bug -- multiple detached
   sweeps/lands writing `.frob/rapid-sweep-baseline.json` concurrently is a
   plausible candidate, given `_resolve_regression_attribution`'s own
   multi-land-between-baselines handling exists for a related reason), or
   the (rule, file) identity is not actually stable between runs (e.g. a
   normalization gap despite T-2036's stated fix), or the checker itself is
   non-deterministic on these specific rules.

100% of the flagged findings in this batch were already `UNATTRIBUTED` with
empty `candidate_commits` from T-1690's symbolic attribution tier -- the
sweep filed them as new regressions anyway, exactly as observed in the prior
T-2538 triage. That "file anyway" behavior is INTENTIONAL per
`_ticket_is_open`'s docstring ("attribution should never suppress a real
regression's own ticket") and is not, by itself, the bug -- an honestly
UNATTRIBUTED finding still needs to surface somewhere, or it becomes the
silent-zero failure mode instead. The bug is upstream of that: these
findings should very often not have been in the "new" set to begin with,
because they are either phantom (class 1) or already-seen-and-baselined
(class 2).

Not fixed in this ticket: `_rapid_sweep.py` is under
`src/frob/app/ticket_runner/` which was OFF LIMITS (leased by another
in-progress agent) for the triage session that found and measured this.
T-1691 (queued, "Bisect the unattributable residue of a red batch") is
Tier 3 of the same attribution ladder but addresses attributing an
UNATTRIBUTED finding to a specific commit within a batch -- a different
problem from a finding recurring identically across MULTIPLE unrelated
batches, which is what was actually measured here. No open ticket found
that owns baseline persistence/recurrence specifically (searched via
`git grep -il sweep -- 'tickets/*/ticket.md'` cross-referenced with
"baseline", and `UNATTRIBUTED`; the done/dropped sweep-regression tickets
found -- T-1901/T-1917/T-1919/T-1923/T-1933/T-1947/T-1988/T-1998 -- are all
single-incident triages, none investigate cross-sweep recurrence).

Suggested investigation, not prescribed as the only fix: (a) instrument
`_write_baseline`/`_read_baseline` to log the identity SET diff (not just
counts) on every sweep, so a recurrence like this one is visible from logs
alone next time instead of requiring manual `git show --stat` archaeology
across four tickets; (b) audit whether `TICK003`/`TICK004`/`COV003`'s
(rule, file) identity generation can point at a path that does not exist
in the tree being checked, and if so which check runs against a stale
tree/cache; (c) check for concurrent-write clobbering of
`.frob/rapid-sweep-baseline.json` when multiple lands' detached sweeps
overlap (plausible given `LANDS IN FLIGHT` routinely shows more than one
land in a busy fleet).
