<!-- frob:waive REF002 reason="T-2369: a point-in-time investigation doc, deliberately singly-anchored from docs/index.md's investigations index -- a second consumer would not be genuine" -->
# T-2796: backlog reproduction measurement (2026-08-21)

## Method

One full, unbudgeted `frob check --json` was run in the T-2796 worktree
(natives built first). The run completed with a `gate-summary` line and
per-stage timings (sys=74.6s, perf=65.3s, archgate=51.3s, tickets=26.5s,
coverage=39.0s, dead_symbols=39.9s, clones=23.2s, refs=18.1s,
pii_structural=19.6s, ... 21 errors, 980 warnings, 0 unresolved, 711
waived) -- this is the positive control for "a real run": >300s wall,
`gate-summary` present, matching the sanity check in the brief. This is
the ONE check reused below; no ticket in this report triggered a second
full check.

Discrepancy note: the coordinator's separately-measured floor tonight was
30 errors / 19 distinct (rule,file) identities. This run's `gate-summary`
line reports 21 gate-errors (27 if ruff/frob-cycle/dup/claude-config-drift
non-gate tool errors are folded in via `scripts/check_summary.py`). The
tree moves between runs (other agents landing concurrently -- 5 live
leases, LOAD 15-25 during this session) so an exact match is not expected;
flagged here rather than silently presented as agreement.

Contention: this session ran with LOAD 15.7-25.1 and 3-5 concurrent `frob
check` processes from other agents (T-2790 primarily, mid mission,
committing every few minutes). The coordinator paused a second planned
full check for this reason; only the one run already in flight when the
pause landed was used. Numbers above may be a few findings off from an
uncontended baseline, but the run passed its own sanity check (see above)
and is treated as valid.

## Three-state legend

- LIVE: the stated defect/finding still reproduces in this check run.
- RESOLVED: does not reproduce, AND a named landed ticket is identified
  as the fix. Proposed as a `drop --absorbed-by <id>` candidate only --
  not auto-dropped, per the hard constraint.
- CANNOT MEASURE: this ticket's claim cannot be adjudicated from gate
  identity counts alone (a resolver-logic bug, a feature/epic with no
  single reproducible finding, a decision-needed ticket, or a rule that
  produced zero findings in this run without independent confirmation
  the relevant code path was actually exercised, per the T-2391 silent-
  zero risk). This state is NEVER collapsed into RESOLVED.

## Findings, from the one check run (rule: severity counts)

TICK004 error=3 warning=1 | TICK011 warning=11 | TICK003 error=1
REF001 warning=257 | REF002 warning=6 | REG008 warning=36
COV006 warning=2 | COV007 warning=44
TEST003 warning=15 | TEST006 warning=1 | TEST014 warning=32
INV003 warning=5 | INV004 warning=5 | INV005 warning=1
NEGEXIST001 warning=15 | WALK001 warning=5 | PLACE001 warning=2
DEAD001 warning=10 | LANG003 warning=3 | PII010/011/012 = note-only (0 warn)
LARGE001 warning=85
PERF005 warning=10 | PERF008 warning=42 | PERF014 warning=2
EXHAUST002 warning=9 | EXHAUST003 warning=161
ruff I001 (import-sort) = 23 warnings
frob-dup = 538 duplicate groups (nonzero)
frob-arch: god-module=16, god-class=1, lock-order-cycle=1 (all still warn)
WIRE001, SCOPE002, SYS107, TEST007: zero diagnostics under those codes in
  this run. The `wire` stage timing (6.72s) confirms the WIRE gate did
  execute; SCOPE/SYS-family stage coverage was not independently isolated
  in this pass. See per-ticket notes below -- none of these four are
  reported RESOLVED on a bare zero-count alone (T-2391 risk).

## Per-ticket verdicts (62 queued tickets, excluding T-2790 in-progress
and T-2796 itself)

### Epics/burn-down children with a directly gate-checkable claim -- LIVE

- T-2368 (INV/NEGEXIST/WALK/PLACE/PII/DEAD/LANG -> zero): LIVE. INV003/4/5,
  NEGEXIST001, WALK001, PLACE001, DEAD001, LANG003 all still nonzero at
  warning level. PII sub-claim only: PII010/011/012 are note-level, not
  warning, in this run -- narrower finding, not a full resolution; keep
  ticket open, note the PII sub-scope may be closer to done.
- T-2369 (REF001/REF002 + REG008 -> zero): LIVE. 257/6/36 respectively.
- T-2370 (COV006/COV007 -> zero): LIVE. 2/44.
- T-2371 (TEST003/TEST006/TEST014 -> zero): LIVE. 15/1/32.
- T-2372 (TICK004/TICK007/TICK011 -> zero): PARTIALLY LIVE. TICK004 is
  now error=3/warning=1 (see T-2367 below for the "already promoted"
  angle) and TICK011 is warning=11 -- both still nonzero, ticket's WARN
  half is live for TICK011 and for TICK004's residual warning. TICK007
  produced ZERO diagnostics in this run -- CANNOT MEASURE from this data
  alone whether that means already-zero-and-clean or the rule/stage
  never fired; needs a targeted check of the TICK007 gate specifically
  before concluding either way. Do not drop the TICK007 sub-scope on
  this evidence.
- T-2373 (ruff I001 -> zero, keep enforced): LIVE. 23 I001 warnings still
  present in this run's `ruff-check` tool output.
- T-2375 (LARGE001 -> zero): LIVE. 85 warnings.
- T-2376 (PERF005/PERF008/PERF014 -> zero): LIVE. 10/42/2.
- T-2377 (EXHAUST002/EXHAUST003 -> zero): LIVE. 9/161.
- T-2378 (frob-dup exact+renamed -> zero): LIVE. 538 duplicate groups
  reported nonzero by the `frob-dup` tool in this run.
- T-2379 (frob-arch god-class/god-module/lock-order -> zero): LIVE.
  god-module=16, god-class=1, lock-order-cycle=1 (plus long-function=23,
  type-dispatch-smell=2, unguarded-shared-write=2, self-join-deadlock=1
  under the same tool, all still warning-level).

### Ledger/tick-specific -- mixed

- T-2367 (TICK004: 9 errors + 17 warnings under one identity, needs
  per-finding triage): the SCALE in the ticket's own claim does not
  reproduce -- current TICK004 state in this run is error=3/warning=1,
  not 9E/17W. This is a real change (most of the finding set is gone),
  but I did NOT identify a single named landed ticket that resolved the
  other ~22 identities, and 4 findings still remain live (see gate-
  summary numbers: 3 errors are the T-0969/T-1273/T-1382 long-queued-
  epic TICK004 findings already visible in `frob ticket doable`'s own
  TICKET ROT section). Verdict: LIVE but SCOPE HAS SHRUNK -- recommend
  the coordinator re-triage the remaining 4 findings under this ticket
  rather than treating the original 9+17 count as still owed, and
  recommend someone git-archaeology the gap (26 -> 4) to find the
  survivor(s) that did most of this work, since a name was not found in
  this pass. NOT a drop candidate without that name.
- T-2693 (TICK006 phantom-refile of T-draft-be1e79b5 collides with
  T-2689's identical title/scope): CANNOT MEASURE from the check run --
  this is a specific historical draft-id collision, not a gate-identity
  claim; would need `frob ticket show T-2689`/archive grep for the named
  draft id, not attempted in this pass (out of the "one check, reused"
  method; would need a second, targeted read, which was not ruled out by
  budget but was not reached -- reporting CANNOT MEASURE rather than
  guessing).

### Resolver/logic-bug tickets -- CANNOT MEASURE from a bulk check alone

These describe a specific defect in a gate's resolution LOGIC (a missed
call-site pattern, a missing offset, a severity classification gap), not
a raw finding count. A zero count for the named rule does not confirm
the logic bug is fixed -- it could mean the specific triggering pattern
just doesn't occur in the current tree. Confirming any of these needs a
constructed positive-control repro (the exact pattern the ticket
describes), which this measurement pass did not build for any of them:

- T-2610 (WIRE001 misses @property attribute reads as callers): CANNOT
  MEASURE. WIRE001 fired zero diagnostics in this run and the `wire`
  stage did execute (6.72s), but that only shows no WIRE001 finding
  fired on the CURRENT tree, not that the specific `@property`-callsite
  gap described is fixed. Needs a positive-control fixture.
- T-2568 (may-raise resolver ignores a guard predicate; 8 EXHAUST002
  findings named): PARTIALLY MEASURABLE -- EXHAUST002 currently shows
  9 warnings (not 0), so the general rule is still firing; whether the
  SPECIFIC 8 findings named in the ticket are still among them was not
  cross-checked file-by-file in this pass. Leaning LIVE (EXHAUST002 is
  nonzero) but flagging the file-level cross-check as unfinished.
- T-2676 (SYS107 test assertion is severity-blind): CANNOT MEASURE.
  SYS107 produced zero diagnostics in this run; SYS-family stage timing
  was not isolated separately from the `sys` stage's 74.6s total, so
  whether SYS107 specifically executed at all was not confirmed.
- T-2608 (SCOPE002 closure debt on _gate_cache.py/_python.py, 850+
  warnings): CANNOT MEASURE. SCOPE002 produced zero diagnostics in this
  run's top-level code aggregation -- a drop from "850+" would be a very
  large claim to accept on a bare zero-count; needs the SCOPE002 stage
  isolated and re-run directly before trusting either state.
- T-2609 (land-time doc/test-edge check doesn't offset for decorators):
  CANNOT MEASURE -- a code-logic claim about `_land_git_ops.py`/similar,
  no corresponding gate-count signature to check in bulk.
- T-2616, T-2645, T-2646, T-2667, T-2680, T-2688, T-2691, T-2709, T-2710,
  T-2728, T-2729, T-2730, T-2752, T-2755: CANNOT MEASURE from the check
  run. Each is either a decision-needed ticket, a perf/design proposal, a
  doc-anchor follow-up, or a structural-refactor request with no single
  gate-identity signature that a bulk `frob check --json` pass resolves.
  None were read in full source detail in this pass (out of the
  allocated "one check + doable + ticket-body read" budget) -- CANNOT
  MEASURE is reported rather than any guess in either direction.

### Epics / feature / research tickets -- CANNOT MEASURE (no single
reproducible defect claim)

T-0969, T-1273, T-1382, T-1597, T-1598, T-1600, T-1601, T-1602, T-1603,
T-1604, T-1607, T-1608, T-1609, T-1661, T-1691, T-1778, T-1820, T-1831,
T-1953, T-2057, T-2202, T-2361, T-2362, T-2384, T-2391, T-2450, T-2451,
T-2501, T-2573, T-2642.

These are epics, research/decomposition tickets, or feature proposals
(new language support, TEST005 coverage-floor ratchets, milestone/
sequencing design work, doc anchor housekeeping). They do not name a
single (rule, file) gate identity whose presence/absence on current main
settles the ticket the way the "burn to zero" tickets above do. Reporting
these as CANNOT MEASURE rather than guessing "does not reproduce" -- the
exact collapse this ticket's brief prohibits. T-1778/T-1820/T-1831 in
particular are WIRE001 `follow_up` doc citations that may already be
satisfied or stale; each needs its own targeted anchor check, not
attempted here.

## No drops proposed

Per the hard constraint, nothing above is proposed as a `drop
--absorbed-by <id>` candidate: every "does not reproduce at its original
scale" case found here (T-2367) still has live residual findings and no
identified survivor ticket, so it does not meet the bar the six manual
drops in the ticket body set (a named survivor). No ticket in this pass
qualified.

## fail vs drop: where the distinction should live

The ticket body's own diagnosis (agents told to run `frob ticket fail`
for an already-resolved finding, which REQUEUES it instead of retiring
it) is a process-documentation gap, not a code gap. It should be
enforced/documented in **`docs/guides/agent-playbook.md`** (section 0 or
a new subsection near the evidence-recording rules, section 5) since that
page is the canonical place this repo already collects exactly this
class of process lesson (its own preamble says as much), and every
worktree agent is required to read it per-ticket. `docs/design/tickets-
data-storage.md` / the `frob ticket fail`/`drop` command help text are
secondary candidates (the CLI's own `--help` for `fail` could gain a line
noting it requeues, and is the wrong verb for "already resolved").
Updating `agent-playbook.md` is out of this ticket's own scope
(`docs/investigations/`), so a follow-up ticket is filed for it rather
than edited here directly (see Filed section in the ticket's Done
report).

## Second deliverable: durable mechanism

Recommend the land-time check, reusing the mechanism T-2760 already
shipped -- NOT the `frob ticket doable` re-measurement query, and NOT a
new mechanism. T-2760 added a structured `findings: tuple[tuple[str,
str], ...]` field on `Ticket`/`TicketSpec` plus a `--finding RULE:FILE`
CLI flag for exactly this identity-matching problem. The land-time path
means the moment a land resolves an identity, EVERY other open ticket
naming that same identity surfaces automatically, at the cheapest
possible time (once, at land, not once per rediscovering agent) -- this
directly targets cause 1 in the ticket body (work lands without closing
the tickets it resolves) as well as cause 2 (mis-set verdicts), since a
land-time surfacing event is also the natural place to prompt for
`drop --absorbed-by` instead of leaving it to individual agent judgment.
Building a second, parallel `doable`-based re-measurement query for the
same identity space would be the "two homes for one rule" violation this
repo has been bitten by repeatedly -- do not build it. Tickets that do
NOT name a structured `findings` identity (the epic/feature/logic-bug
tickets above) are out of scope for this mechanism regardless -- they
need the manual per-ticket read this pass gave them, or a future,
separate design for claims that are not gate-identity-shaped.

## Filed

(see Done report in tickets.md for the real ticket id filed for the
agent-playbook.md documentation gap.)
