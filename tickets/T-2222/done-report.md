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
