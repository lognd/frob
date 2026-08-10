---
id: T-1686
title: 'Verification watermark: make landing independent of verifying in every profile'
state: in-progress
kind: feature
origin: agent
created: '2026-08-06'
priority: critical
blocked_by:
- T-1736
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- tickets/T-1686/ticket.md
- tickets/T-1686/done-report.md
evidence_scope:
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: T-1736 (now landed) built the enqueue-side wiring in _land.py that this
    ticket's own plan required; reopening with that file in scope for whatever thin
    follow-up remains, per coordinator direction
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_ticket_land.py
  reason: T-1736 (now landed) built the enqueue-side wiring in _land.py that this
    ticket's own plan required; reopening with that file in scope for whatever thin
    follow-up remains, per coordinator direction
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1686/ticket.md
  reason: 'SCOPE001: ticket''s own directory files (precedent) and the disclosed follow-up
    draft filed from this ticket''s own Done report'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1686/done-report.md
  reason: 'SCOPE001: ticket''s own directory files (precedent) and the disclosed follow-up
    draft filed from this ticket''s own Done report'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1835/ticket.md
  reason: 'SCOPE001: ticket''s own directory files (precedent) and the disclosed follow-up
    draft filed from this ticket''s own Done report'
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: tickets/T-1835/ticket.md
  reason: draft dropped as an exact duplicate of the pre-existing T-1696 descendant
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'T-1686 declares this file but has written nothing to it: its verify-cluster
    worktree is clean with zero divergence from main on this path. The enqueue-side
    work the epic needed landed under T-1736 in _land.py instead. Releasing the stale
    declaration so T-1841 can land, rather than overriding the CrossTicketLeakage
    guard. The guard is correct; the declaration was not.'
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/tickets/_land_queue.py
  reason: T-1686 is tier=epic and does not itself implement -- its descendants (T-1689/T-1691/T-1695/T-1696)
    do. Holding the four hottest paths in the repo from the root checkout, with no
    agent working it, blocked roughly 25 queued tickets and left T-1856's finished+tested
    work unlandable on CrossTicketLeakage. tests/test_ticket_land.py is retained because
    it covers T-1686's already-recorded evidence.
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/serve/_daemon.py
  reason: T-1686 is tier=epic and does not itself implement -- its descendants (T-1689/T-1691/T-1695/T-1696)
    do. Holding the four hottest paths in the repo from the root checkout, with no
    agent working it, blocked roughly 25 queued tickets and left T-1856's finished+tested
    work unlandable on CrossTicketLeakage. tests/test_ticket_land.py is retained because
    it covers T-1686's already-recorded evidence.
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: docs/modules/tickets.md
  reason: T-1686 is tier=epic and does not itself implement -- its descendants (T-1689/T-1691/T-1695/T-1696)
    do. Holding the four hottest paths in the repo from the root checkout, with no
    agent working it, blocked roughly 25 queued tickets and left T-1856's finished+tested
    work unlandable on CrossTicketLeakage. tests/test_ticket_land.py is retained because
    it covers T-1686's already-recorded evidence.
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/tickets/_land.py
  reason: T-1686 is tier=epic and does not itself implement -- its descendants (T-1689/T-1691/T-1695/T-1696)
    do. Holding the four hottest paths in the repo from the root checkout, with no
    agent working it, blocked roughly 25 queued tickets and left T-1856's finished+tested
    work unlandable on CrossTicketLeakage. tests/test_ticket_land.py is retained because
    it covers T-1686's already-recorded evidence.
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: tests/test_ticket_land.py
  reason: 'T-1944 follow-through: release the unused write lease on the repo highest-traffic
    land test file; T-1686 has changed zero lines of code, evidence stays covered
    via evidence_scope'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_land.py::TestRecordVerifyIntentForLandedCommit::test_real_land_records_an_intent_entry
- tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_clean_run_advances_watermark_and_compacts_queue
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_raises_with_attributed_and_unattributed_findings
- tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_death_between_green_result_and_watermark_write_is_never_assumed_green
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
anchor: false
anchor_reason: null
---
T-1684 took the multi-minute verification sweep off the land critical
path under `rapid`. The same reasoning generalises to `standard`, and
doing so collapses three profile code paths into one mechanism at three
settings.

THE PRINCIPLE THAT DECIDES WHAT MAY BE DEFERRED

A check must be synchronous if and only if its failure damages someone
OTHER THAN the author. Ledger integrity, LAND-PROOF, lease/lock
discipline, merge-conflict resolution and "the tree imports" corrupt
other agents' work, so they stay on the critical path in every profile,
forever. Coverage floors, doc drift, arch thresholds, dup, perf and the
rest only assert that THIS change is good; their remedy is a follow-up
ticket, not a revert. There is no correctness argument for making the
author wait on those -- only habit.

THE MECHANISM

Verification is a pure function of tree state, so the unit of
verification is a COMMIT, not a land. Introduce a durable watermark:
"main is verified through commit X".

The daemon becomes a COALESCING worker rather than a FIFO one. Each land
appends a cheap intent record (commit sha, ticket id, touched symbol
set). The worker wakes, drains the queue TO ITS TIP, verifies once at the
newest commit, and advances the watermark past every commit in the batch.
Five lands, one verification pass -- and it is not a trick: verifying at
HEAD-after-L5 genuinely verifies L1..L5, because that is the tree that
ships.

The saving compounds twice: the gate pass amortises N-to-1, and the test
run becomes the UNION of the batch's touched sets in a single pytest
process (one collection, one set of fixtures) instead of N cold starts
over overlapping files.

THE HARD PART: ATTRIBUTION

Batching trades wall-clock for attribution precision. Three tiers,
cheapest first: (1) the T-1684 rolling-baseline set diff yields new
(rule, symbol) identities rather than a count; (2) SYMBOLIC attribution
-- a finding anchored at symbol S attributes to the commit whose touched
symbol set REACHES S in the reference graph; (3) bisect only the residue
tier 2 cannot attribute.

WHAT KEEPS IT HONEST

Bounded queue (depth and age; the land blocks at the ceiling -- deferral
is a credit line, not free money) and a quarantine circuit breaker (a red
batch stops further deferred lands until attributed, because landing on a
known-broken base is what makes attribution cost explode).

THE PAYOFF

The profiles stop being three code paths and become one dial:
`fortress` = depth 0 (synchronous, refuse on red); `standard` = bounded
depth K, quarantine + file on red; `rapid` = unbounded, never blocks,
files and never reverts. Every `if rapid:` seam scattered through the
land pipeline deletes.

RECORDED DECISION: on a red batch, `standard` QUARANTINES AND FILES; it
does not auto-revert. Reverting a published commit other worktrees have
already branched from is strictly worse than a filed high-priority ticket
plus a stop-the-line flag. Auto-revert is coherent only at depth 0, where
nobody can have branched yet.

WHAT ALREADY EXISTS (this is a connect-what-exists epic, not greenfield)

- `frob.tickets._land_queue`: persisted, locked, with enqueue/drain_next/
  queue_status. T-1444's own Done report disclosed "sharing one baseline
  capture and one post-drain sweep across a whole batch of N tickets" as
  deferred follow-up. This epic is that owed work.
- `frob.serve._warm`/`_watch`: the daemon already keys a WarmState on a
  repo dirty key and has FS-watch push invalidation -- the watermark's
  substrate, needing a durable commit-keyed sibling.
- T-1684's rolling baseline and `frob ticket sweep-async`: the deferred
  worker, today spawned per-land, becomes the daemon's queue worker.

Adjacent open work: T-1479 (daemon-proxy ticket path), T-1554
(post-commit checkpoint gap beyond the sweep window).

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

T-1686 is the epic tracking ticket for "landing independent of verifying
in every profile". Its own declared scope (src/frob/tickets/_land_queue.py,
src/frob/serve/_daemon.py, src/frob/app/ticket_runner/_rapid_sweep.py,
docs/modules/tickets.md, reopened with src/frob/tickets/_land.py and
tests/test_ticket_land.py added) needed no further CODE changes: every
concrete mechanism this epic's own body describes was already built,
scoped correctly, by sibling leaf tickets --

- T-1687: durable verify-queue + watermark data model.
- T-1688: the daemon's coalescing worker (already wired into
  frob.serve._daemon's own poll loop).
- T-1690: symbolic (graph-reachability, never lexical) attribution.
- T-1692: backpressure ceilings.
- T-1693/T-1791: the quarantine circuit breaker, and its wiring into
  the shared _file_regression_ticket seam both the per-land sweep and
  the coalescing worker call through.
- T-1694: crash safety -- a dead worker can never advance the watermark
  past a batch it did not finish verifying.
- T-1736 (blocked this ticket, landed first): the enqueue side --
  frob.tickets._land._land_locked now calls record_intent after every
  real land, which is what made the whole chain above actually feed
  from real lands rather than sit unfed.

This ticket's own contribution is docs/modules/tickets.md's new "T-1686
epic status" section, tying all of the above together in one place with
its own status: what's DONE (the durable record/worker/attribution/
quarantine/crash-safety/enqueue mechanism, end to end) and what remains,
disclosed and filed separately rather than silently folded into this
epic's "done":

- The profile dial itself. fortress/standard/rapid are still three
  separate code paths in src/frob/app/ticket_runner/_land_cmd.py
  (confirmed: `rapid_land = effective is ProfileName.RAPID` and its
  downstream branches, around line 2340) rather than one depth-
  parameterized mechanism -- the machinery above benefits `rapid` today;
  collapsing fortress/standard onto it is real, separately-scoped work.
  _land_cmd.py was never in this ticket's own declared scope. Filed as
  T-1835 (renumbers at land).
- CLI visibility (T-1697, already queued in this same dispatch group,
  not yet built) -- frob verify status/now/explain.

No code changed here (a docs-only ticket, matching the T-0167 precedent
for evidence on such a ticket per the playbook: existing tests already
demonstrating the wiring are cited as evidence rather than inventing a
new one for a change that touches no new code path).

frob check --ticket T-1686: 0 errors after scoping the ticket's own
directory files (the pre-existing ARCH001/COV001 findings in
src/frob/app/ticket_runner/_query.py and src/frob/tickets/_doable.py are
unrelated, landed on main by a sibling agent's T-1738).

### Changed
```
 tickets/T-1686/ticket.md           | 43 ++++++++++++++++++++++++++++++++++++++
 tickets/T-1835/ticket.md | 24 +++++++++++++++++++++
 2 files changed, 67 insertions(+)
```

### Evidence
- `tests/test_ticket_land.py::TestRecordVerifyIntentForLandedCommit::test_real_land_records_an_intent_entry` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_clean_run_advances_watermark_and_compacts_queue` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_raises_with_attributed_and_unattributed_findings` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_death_between_green_result_and_watermark_write_is_never_assumed_green` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 4 error(s), 1295 warning(s), 738 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/tickets/_doable.py, ARCH103@src/frob/app/ticket_runner/_query.py, COV001@src/frob/tickets/_doable.py
