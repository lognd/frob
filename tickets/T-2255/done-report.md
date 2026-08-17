## Done report

Changed:
- `frob.tickets._land._OrphanEvidenceCheckOutcome` (new StrEnum: RAN /
  SKIPPED_UNMEASURED)
- `frob.tickets._land._LAST_ORPHAN_EVIDENCE_OUTCOME` (new process-local
  dict, the T-2091 pattern for this second land-time check)
- `frob.tickets._land._check_orphaned_evidence_deletion` (records the
  outcome at every branch; the three skip early-outs now log at WARNING
  instead of DEBUG, naming the skip explicitly as `SKIPPED-UNMEASURED`)

Evidence (all in `tests/unit/test_land_orphaned_evidence.py`, new class
`TestOrphanEvidenceCheckOutcome` unless noted):
- `test_skipped_unmeasured_recorded_and_logged_on_collection_failure`
  (acceptance 0, 4 -- MUST-FAIL-FIRST proof, `--check-repro` verified
  FAILED_AT_PARENT against `2c3c70bd2`)
- `TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test`
  (acceptance 1, pre-existing T-1946 test, still passes)
- `TestOrphanedEvidenceDeletion::test_deletion_of_unbound_test_lands_cleanly`
  (acceptance 2, pre-existing T-1946 MUST-STILL-PASS control, still
  passes)
- `test_skipped_unmeasured_does_not_block_the_land` (acceptance 3)
- `test_ran_recorded_on_healthy_pass` (acceptance 4)
- `test_ran_recorded_even_when_check_refuses` (companion, not bound to
  an acceptance index -- documents that a refusal is its own
  unmistakable Err and does not need a separate RAN/SKIPPED marker)

Filed:
- T-2275 -- follow-up to wire `_LAST_ORPHAN_EVIDENCE_OUTCOME`
  into `_print_land_proof`'s `LAND-PROOF:` line (`orphan_evidence_check=`
  field), T-2091 parity. Out of T-2255's declared scope
  (`src/frob/tickets/_land.py` alone; T-2091's equivalent work paired
  `_land.py` with `_land_cmd.py`). T-2255's own acceptance 5 is met
  without it: the skip is surfaced via a WARNING-level log line in the
  land's own console output plus the in-process outcome dict, not
  silent -- but the LAND-PROOF line itself doesn't carry the field yet.
- T-2274 -- separate incident found while implementing this
  ticket: a "record land commit" bookkeeping commit for an UNRELATED
  ticket (T-2256, commit `9a7bf279657b8b15543079f6a11a0d4abb7aeb98`)
  absorbed a bystander's dirty, in-progress edit to `_land.py` sitting
  in the shared root at the time -- a 32-line diff with zero
  ticket/evidence/test trail, and a broken partial state (referenced
  symbols with no definition -- a guaranteed NameError on the very code
  path T-2255 touches). Not this ticket's mechanism to fix (land-commit
  staging, not the orphan-evidence check), but T-2255's own land repairs
  the broken code as a side effect (it adds the missing definitions,
  now correct and tested).

Gates: `frob check --ticket T-2255` run per-family (`gates-fast`,
`gates-native`, `gates-security`, `lint`, `static`) under `FROB_AGENT`
(the full/unchunked run refuses under the agent env by design, T-0627).
Zero findings in either file this ticket touches
(`src/frob/tickets/_land.py`, `tests/unit/test_land_orphaned_evidence.py`)
across all five; the pre-existing repo-wide counts (89/16/9 errors etc.)
are unscoped baseline noise per `frob check`'s own NOTE ("counts above
are REPO-WIDE, not filtered to this ticket") and predate this change.
`ruff format`/`ruff check` clean on both touched files.

`frob test --base main` (with `FROB_AGENT`/`FROB_WORKTREE` unset --
those vars trip an unrelated worktree-lease guard against pytest's OWN
tmp-dir git fixtures, an environment artifact of running the suite
inside a leased worktree, not a real failure; confirmed by re-running
with the guard-tripping vars unset) -- exit=0, all selected tests pass.

`frob ticket evidence T-2255 --check-repro --base-ref 2c3c70bd2` ->
FAILED_AT_PARENT (genuine repro: the repro-test commit was made BEFORE
the fix commit, and fails on unfixed code with an `ImportError` for the
not-yet-defined `_LAST_ORPHAN_EVIDENCE_OUTCOME`/
`_OrphanEvidenceCheckOutcome`).

## What a genuinely-uncollectable worktree does now (acceptance 3)

Unchanged verdict, changed visibility: `_check_orphaned_evidence_
deletion` still returns `Ok(None)` on a `collect_python_tests` failure
(hard-failing would block the entire fleet on a routine, not-yet-built-
natives environment artifact -- explicitly ruled out by this ticket's
own brief as a worse outcome than the bug). What changed: the skip is
recorded as `_OrphanEvidenceCheckOutcome.SKIPPED_UNMEASURED` in
`_LAST_ORPHAN_EVIDENCE_OUTCOME` (inspectable in-process, e.g. by tests)
and logged at WARNING (not the pre-fix DEBUG) with the literal token
`SKIPPED-UNMEASURED`, so the land's own console output says so instead
of staying indistinguishable from a genuine pass.

### Changed
```
 src/frob/tickets/_land.py                 |  90 ++++++++++---
 tests/unit/test_land_orphaned_evidence.py | 202 +++++++++++++++++++++++++++++-
 tickets/T-2255/ticket.md                  |  56 ++++++++-
 tickets/T-2274/ticket.md        |  96 ++++++++++++++
 tickets/T-2275/ticket.md        |  58 +++++++++
 5 files changed, 475 insertions(+), 27 deletions(-)
```

### Evidence
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanEvidenceCheckOutcome::test_skipped_unmeasured_recorded_and_logged_on_collection_failure` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanEvidenceCheckOutcome::test_ran_recorded_on_healthy_pass` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanEvidenceCheckOutcome::test_ran_recorded_even_when_check_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanEvidenceCheckOutcome::test_skipped_unmeasured_does_not_block_the_land` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_deletion_of_unbound_test_lands_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/fleet_status.py, COV001@src/frob/scaffold/_skills_sync.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@src/frob/scaffold/_skills_sync.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC007@src/frob/tickets/_land.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@src/frob/tickets/_land.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2255/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2255/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2255, RENDER001@src/frob/release/_cli.py, RENDER001@src/frob/scaffold/_skills_sync.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
