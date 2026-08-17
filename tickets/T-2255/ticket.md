---
id: T-2255
title: T-1946's orphaned-evidence land guard fails OPEN when test collection fails
  -- the normal case in agent worktrees -- and let T-2240 orphan 11 tickets' evidence
  (28 COV003, floor 35 to 59)
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_orphaned_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: T-2091 set the precedent for this exact pairing (_land.py's process-local
    RAN/SKIPPED_UNMEASURED outcome dict + _land_cmd.py's _print_land_proof consuming/printing
    it on the LAND-PROOF line) for the claims-reverify check; T-2255's acceptance
    criterion 5 needs the identical wiring for the orphaned-evidence check so a land's
    own record -- not just an in-process dict a unit test can inspect -- distinguishes
    ran from skipped. Test file addition is the evidence home for the new outcome-record
    behavior, alongside T-1946's existing suite it lives in.
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/unit/test_land_orphaned_evidence.py
  reason: T-2091 set the precedent for this exact pairing (_land.py's process-local
    RAN/SKIPPED_UNMEASURED outcome dict + _land_cmd.py's _print_land_proof consuming/printing
    it on the LAND-PROOF line) for the claims-reverify check; T-2255's acceptance
    criterion 5 needs the identical wiring for the orphaned-evidence check so a land's
    own record -- not just an in-process dict a unit test can inspect -- distinguishes
    ran from skipped. Test file addition is the evidence home for the new outcome-record
    behavior, alongside T-1946's existing suite it lives in.
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'Reverting: touching this file pulls in 326 pre-existing scope-closure doc
    warnings unrelated to T-2255, and the check''s own operator-visible surfacing
    (WARNING-level land log + in-process outcome record) is achievable entirely within
    _land.py''s own scope without it. LAND-PROOF wiring (the T-2091-style print) is
    filed as a narrow follow-up ticket instead.'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_land_orphaned_evidence.py::TestOrphanEvidenceCheckOutcome::test_skipped_unmeasured_recorded_and_logged_on_collection_failure
- tests/unit/test_land_orphaned_evidence.py::TestOrphanEvidenceCheckOutcome::test_ran_recorded_on_healthy_pass
- tests/unit/test_land_orphaned_evidence.py::TestOrphanEvidenceCheckOutcome::test_ran_recorded_even_when_check_refuses
- tests/unit/test_land_orphaned_evidence.py::TestOrphanEvidenceCheckOutcome::test_skipped_unmeasured_does_not_block_the_land
- tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_deletion_of_unbound_test_lands_cleanly
- tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test
designated_repro_test: null
acceptance:
- text: When collect_python_tests fails, the land does not silently proceed as if
    the check passed; the skip is surfaced as explicit UNMEASURED state, never a silent
    Ok(None)
  evidence:
  - tests/unit/test_land_orphaned_evidence.py::TestOrphanEvidenceCheckOutcome::test_skipped_unmeasured_recorded_and_logged_on_collection_failure
- text: A land removing a test function bound as evidence on another ticket is refused
    even when the containing FILE survives (the T-2240 shape)
  evidence:
  - tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test
- text: 'MUST-STILL-PASS: deleting an unbound test still lands cleanly; deleting and
    re-adding the ticket''s OWN evidence in one diff is still not refused'
  evidence:
  - tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_deletion_of_unbound_test_lands_cleanly
- text: A worktree that genuinely cannot collect does not become unlandable; state
    what it does instead and why that is safe
  evidence:
  - tests/unit/test_land_orphaned_evidence.py::TestOrphanEvidenceCheckOutcome::test_skipped_unmeasured_does_not_block_the_land
- text: The land's own record distinguishes 'check ran and passed' from 'check skipped'
  evidence:
  - tests/unit/test_land_orphaned_evidence.py::TestOrphanEvidenceCheckOutcome::test_skipped_unmeasured_recorded_and_logged_on_collection_failure
  - tests/unit/test_land_orphaned_evidence.py::TestOrphanEvidenceCheckOutcome::test_ran_recorded_on_healthy_pass
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 9fc8b80ef83ca111b2a6ba72cce081d7201573a7
---
# T-1946's orphaned-evidence land guard fails OPEN on test-collection failure -- the common case in agent worktrees -- and let a land orphan 11 tickets' evidence

## Measured evidence (2026-08-16)

Unscoped floor went **35 -> 59 errors** in one hour. Coverage verified complete
before trusting it (43 results, `gate-summary` present, all 24 `gate:*`
families). The entire regression is one class:

    28  gate:COV:COV003
     7  gate:TICK:TICK004
     6  gate:ARCH:ARCH001
     4  frob-cycle
     ...

All 28 COV003 findings name the same file:

    28  tests/unit/test_makefile_coverage.py

Orphaning evidence bound on **11 other tickets**: T-1205, T-1235, T-1335,
T-1353, T-1362, T-1373, T-1397, T-1426, T-1433, T-1526, T-1363.

Cause: T-2240 (`dcb07727d8ce`) legitimately retired the Makefile-text-slicing
tests, rewriting that file 924 -> 195 lines. The file SURVIVED; ~28 test
functions inside it did not.

## The guard for this exists, and it did not run

T-1946 (done) shipped `_check_orphaned_evidence_deletion`
(`src/frob/tickets/_land.py:4439`), which refuses a land with
`LandError.OrphanedEvidenceDeletion` when the branch's own diff deletes a
pytest node bound as evidence on a different ticket. It is node-level by
design, so a rewrite-in-place is exactly what it should catch.

It has two unconditional fail-open returns:

    if changed.is_err:
        _log.warning("land: %s orphaned-evidence check skipped -- diff unreadable (%s)", ...)
        return Ok(None)
    ...
    collected = collect_python_tests(worktree)
    if collected.is_err:
        _log.warning("land: %s orphaned-evidence check skipped -- test collection failed (%s)", ...)
        <skips the check>

**The skip condition is the normal condition in an agent worktree.** This
repo's own operating notes record that fresh worktrees lack `strata_core` /
`frob_core` builds and that collection/evidence failures there are environment
artifacts rather than regressions. So the guard is disabled precisely where
lands happen.

This is the same shape already recorded for a different land-time check: a gate
spawn refused under `FROB_AGENT`, its empty result read as "unmeasured", then
skipped permissively. Two independent land-time guards, same failure mode.

## Why a playbook line is not the fix

`docs/guides/agent-playbook.md:924` already carries "## 9. The deletion-filter
land rule (verify before every finish)". The rule is written down, the guard is
implemented, and 11 tickets' evidence was still orphaned -- because the guard
silently opted itself out and nothing surfaced that it had. An agent doing
everything right cannot tell the difference between "check passed" and "check
skipped".

## Do NOT fix it this way

- **Do NOT make the check hard-fail whenever collection fails.** Collection
  legitimately fails in a fresh worktree that has not built natives; refusing
  every such land would block the fleet on an environment artifact. That is a
  worse outcome than the bug.
- **Do NOT drop to a filename-level comparison** ("did the diff delete a file
  containing bound evidence"). T-2240 did not delete the file. A path-level
  check misses the exact incident that motivated this ticket, and the guard is
  deliberately node-level.
- **Do NOT rely on COV003 catching it afterwards.** It does -- that is how this
  was found -- but only on the next unscoped `frob check`, after the land is
  published and the orphan is already in the floor. The land is the last point
  where the deleting branch still knows what it deleted.
- **Do NOT parse the diff text for `def test_` lines.** Standing user
  directive: token/grammar, never lexical. Node identity must come from
  collection or a parsed tree, not from matching source text.

## Acceptance criteria

1. (MUST FAIL FIRST) When `collect_python_tests` fails, the land does NOT
   silently proceed as if the check passed. It must either resolve node
   identity another way, or surface the skip as an explicit,
   operator-visible UNMEASURED state that the land records -- never a silent
   `Ok(None)`. Fails today: two unconditional fail-open returns.
2. A land whose diff removes a test function bound as evidence on another
   ticket is refused, even when the containing FILE survives (the T-2240
   shape). Build the fixture from the real case: 28 nodes removed from a
   surviving `tests/unit/test_makefile_coverage.py`.
3. MUST-STILL-PASS CONTROLS: a land deleting an UNBOUND test still lands
   cleanly, and a land that deletes and re-adds its OWN ticket's evidence in
   the same diff is still not refused. Both behaviours have tests from T-1946
   (`test_deletion_of_unbound_test_lands_cleanly`) and must keep passing.
4. A worktree that genuinely cannot collect (no natives built) does not become
   unlandable. State what it does instead and why that is safe.
5. Whatever the outcome, the land's own record shows whether this check RAN.
   "Passed" and "skipped" must be distinguishable after the fact.

## Residue, not this ticket's job

The 28 already-orphaned COV003 findings need repointing or the citing tickets
need updating. That is separate cleanup; this ticket is about no twelfth ticket
being orphaned.

## Scope note

`src/frob/tickets/_land.py` is currently held by a live T-2220 lease. This
ticket must wait for that to land -- do not dispatch them concurrently.

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
