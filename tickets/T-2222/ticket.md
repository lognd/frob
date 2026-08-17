---
id: T-2222
title: fleet_status reports a raw lease COUNT with concurrency guidance attached,
  so reclaimable and root-residual leases read as live agents (6 leases = 4 agents)
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- docs/guides/coordinator-scripts.md
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_coordinator_scripts.py::TestLeaseClassification::test_holder_dead_is_reclaimable
- tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_guidance_line_uses_live_count_not_raw_count
- tests/unit/test_coordinator_scripts.py::TestLeaseClassification::test_root_worktree_is_structurally_unreclaimable
- tests/unit/test_coordinator_scripts.py::TestLeaseClassification::test_live_lease_stays_live
- tests/unit/test_coordinator_scripts.py::TestLeaseClassification::test_classification_is_strictly_read_only
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestLeaseClassification::test_holder_dead_is_reclaimable
acceptance:
- text: 'The report distinguishes a reclaimable lease from a live one (fails today:
    leases() returns undifferentiated records)'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestLeaseClassification::test_holder_dead_is_reclaimable
- text: The concurrency guidance clause is computed from the LIVE count, not the raw
    file count
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_guidance_line_uses_live_count_not_raw_count
- text: A lease whose worktree IS the repo root is reported as structurally unreclaimable,
    derived from the record's worktree vs resolved root -- never a ticket-id allowlist
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestLeaseClassification::test_root_worktree_is_structurally_unreclaimable
- text: A genuinely live lease MUST STILL report as live (must-still-pass control
    against a fix that marks everything reclaimable)
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestLeaseClassification::test_live_lease_stays_live
- text: 'The report remains strictly read-only: it never releases, modifies, or deletes
    a lease'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestLeaseClassification::test_classification_is_strictly_read_only
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# fleet_status reports a raw lease COUNT and attaches concurrency guidance to it, so reclaimable and permanently-residual leases read as live agents

## Measured evidence (2026-08-16)

`scripts/fleet_status.py` prints, on one line:

    LOAD 13.1  MEM 13.3GB avail  6 lease(s) -- guidance is 3-4 agent concurrent

The count comes from `leases()` (`scripts/fleet_status.py:108`), which globs
`.git/frob-leases/*.json` and returns every record. It performs NO liveness
classification -- there is no `reclaimable`/`stale`/`live` distinction
anywhere in the script.

The guidance clause ("guidance is 3-4 agent concurrent") is attached directly
to that raw number, which makes it a de-facto concurrency governor. Measured
today, of those 6 leases:

- **T-1382** -- `state: queued`, scope `src/frob/**` + `docs/**`, recorded
  2026-08-10 (6 days). `frob worktree release-lease T-1382` reclaimed it
  IMMEDIATELY via `reason=holder-dead`. It was reclaimable the entire time.
- **T-1686** -- recorded against the SHARED ROOT. Liveness is decided by
  `scan_for_live_worktree_process` ("is any process cwd'd into the worktree",
  `_leases.py:1605`); 53 processes were cwd'd into the root at the time of
  measurement, so it reads live permanently. This is **T-2007, already done**,
  whose report states the fix was prevention-only and that "T-1686 itself is
  untouched by this fix". It is accepted permanent residue.

So 6 leases meant 4 live agents. Two of the six could never have been agents.

## Why this is not cosmetic

The coordinator repeatedly held dispatch citing this number while at or below
the actual cap -- directly costing throughput against a 5-min/land target that
was running at ~12 min/land. The number is the input to a throttling decision,
and it silently overstates by the number of dead/residual leases.

This is a recurring defect SHAPE in this repo, not a one-off:
`ps aux | grep -c` counting ~4 lines per land produced a "15-16 concurrent
lands" report when there were 4; a `head -6` truncation of this same lease
list produced a false "an agent abandoned its work" conclusion. Each time, a
summary number included entries that did not mean what the reader assumed.

## Do NOT fix it this way

- **Do NOT fix this in the operator's head.** A memory note ("effective
  concurrency = LEASES minus 1") is exactly the non-fix this repo's standing
  audit duty forbids: it is a rule that must be remembered at the moment of
  reading, which is the moment it has already been forgotten. The report must
  carry the distinction.
- **Do NOT hardcode T-1686 (or any ticket id) as a known-residue exception.**
  An id-keyed exception silently stops being correct the moment that ticket
  closes or another root lease appears. Classify by the RECORD's properties
  (worktree == repo root, ledger state, recorded_at age), not by identity.
- **Do NOT decide liveness by parsing `ps` output or counting processes.**
  That is the precise miscount cited above. Use `/proc/<pid>/cwd` resolution
  (the mechanism `_leases.py` itself uses) or the lease record's own fields.
- **Do NOT infer anything from the lease FILENAME or the worktree path's
  shape.** A series agent works several tickets in ONE worktree, so
  `T-2203`'s lease legitimately pointed at `.claude/worktrees/t2201-series`.
  Read the record's `worktree` field; do not pattern-match the path against
  the ticket id. This is a token/grammar-vs-lexical requirement, not a style
  preference.
- **Do NOT auto-release anything.** This ticket is about REPORTING. A status
  command that mutates lease state is a much larger and riskier change, and
  releasing a live lease is a serious failure.

## Acceptance criteria

1. (MUST FAIL FIRST) A test asserting the report distinguishes a reclaimable
   lease from a live one -- e.g. a fixture with one live lease and one
   holder-dead lease produces a report naming which is which. Fails today:
   `leases()` returns undifferentiated records. Confirm `--check-repro` reads
   FAILED_AT_PARENT before the fix commit.
2. The concurrency guidance clause is computed from the LIVE count, not the
   raw file count. If 6 leases contain 2 non-live, the line must not imply 6
   agents.
3. A lease whose worktree IS the repo root is reported as structurally
   unreclaimable, derived from comparing the record's `worktree` against the
   resolved repo root -- NOT from a ticket-id allowlist.
4. A genuinely live lease MUST STILL be reported as live (must-still-pass
   control). A change that marks everything reclaimable would satisfy 1-3 and
   is catastrophic -- it would invite releasing a live agent's lease.
5. The report does not release, modify, or delete any lease. Read-only.

## Scope note

`scripts/fleet_status.py` is the consumer. If the classification logic
genuinely belongs in `frob.tickets._leases` (which already owns
`lease_staleness_reason` and `scan_for_live_worktree_process`) rather than
being re-implemented in the script, say so and propose that instead -- the
script deliberately stays import-light (see its own comment at :97), so this
is a real design call, not an obvious one. Re-implementing staleness rules in
a second home is the defect shape T-1966 covers; if you must duplicate, say
why explicitly.

## Done report

Added scripts/fleet_status.py::lease_classification, classifying each
held lease record as "live"/"reclaimable"/"root-resident", mirroring
frob.tickets._leases.lease_staleness_reason's own four staleness shapes
(path-gone/ticket-gone/ticket-terminal/holder-dead -> reclaimable) plus
one addition: a lease whose worktree resolves to this repo's own root
reports "root-resident" (T-1686's real shape), derived purely from
comparing the record's own worktree field against the resolved repo
root -- never a ticket-id allowlist. live_lease_count sums the "live"
bucket.

The LOAD line's concurrency guidance clause and the LEASES section
header now both key off the live count, not len(leases()); each LEASES
row also prints its own classification. Report stays strictly read-only
-- confirmed by a dedicated test that monkeypatches Path.unlink to raise
if called at all while classifying a batch including a reclaimable and a
root-resident record.

Scope note (per T-2222's own scope note): classification logic stays
duplicated in fleet_status.py rather than imported from
frob.tickets._leases, per the script's existing "no frob import"
contract (it must run under any interpreter on PATH, not just inside
this repo's own venv) -- same posture as _rot_day_thresholds/
quarantine_state, which already mirror frob gate logic in plain form for
the identical reason.

Repro: tests/unit/test_coordinator_scripts.py::TestLeaseClassification::
test_holder_dead_is_reclaimable, confirmed FAILED_AT_PARENT at
0ba5a179f7a21b4742c443f93e86a25acedf5d52 (the repro-only commit -- the
function did not exist on main at all).

Must-still-pass control: TestLeaseClassification::
test_live_lease_stays_live -- a genuinely live lease (worktree exists,
ticket in-progress on main, well within TTL) still reports "live".

### Changed
```
 docs/guides/coordinator-scripts.md     |  72 +++++++++--
 scripts/fleet_status.py                | 222 ++++++++++++++++++++++++++++++---
 tests/unit/test_coordinator_scripts.py | 186 ++++++++++++++++++++++++++-
 tickets/T-2222/ticket.md               |  27 ++--
 4 files changed, 472 insertions(+), 35 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestLeaseClassification::test_holder_dead_is_reclaimable` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_guidance_line_uses_live_count_not_raw_count` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLeaseClassification::test_root_worktree_is_structurally_unreclaimable` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLeaseClassification::test_live_lease_stays_live` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLeaseClassification::test_classification_is_strictly_read_only` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t2200-series/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t2200-series/tests/test_ticket_work_and_land_finish.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2222, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
