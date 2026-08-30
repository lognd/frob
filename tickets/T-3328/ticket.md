---
id: T-3328
title: TestArchive's 5 baseline failures are git worktree list exit 128 under load
  hitting T-3230's new fail-closed path
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/_archive.py
  reason: T-3442 holds a live lease on _archive.py; fixing via test fixture git-init
    instead, no code-side edit needed
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_tickets.py
  reason: T-3442 holds a live lease on _archive.py; fixing via test fixture git-init
    instead, no code-side edit needed
  actor: logan
  at: '2026-08-29'
body_changes:
- mode: append
  reason: 'record a confound I introduced: I reaped five worktrees while EK was measuring
    these exact tests, and git worktree remove mutates the list that git worktree
    list reads -- the current failure evidence is contaminated and needs re-measurement
    under three stated controls'
  actor: logan
  at: '2026-08-29'
  old_length: 4369
  new_length: 7151
- mode: append
  reason: deterministic root cause found on a quiet box with no concurrent worktree
    mutation; supersedes the host-contention hypothesis and clears the contamination
    warning
  actor: logan
  at: '2026-08-29'
  old_length: 7151
  new_length: 11545
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TWO INDEPENDENT OBSERVATIONS OF THE SAME FIVE TESTS, connected here.

1. Series DS's full chunked baseline of main listed these five in cluster J as
   UNCHARACTERIZED, with no shared root cause found:

       tests/test_tickets.py::TestArchive::test_idempotent_second_run_moves_nothing
       tests/test_tickets.py::TestArchive::test_moves_done_and_dropped_only
       tests/test_tickets.py::TestArchive::test_load_queue_merges_active_and_archive
       tests/test_tickets.py::TestArchive::test_new_ticket_id_continues_past_archived_max
       tests/test_tickets.py::TestArchive::test_blocked_by_archived_ticket_resolves_closed

2. Series DX, working an unrelated ticket, independently observed the same five
   failing on `git worktree list` EXIT 128 under heavy host load, and noted it
   reproduced only under contention, not deterministically. It correctly
   declined to file on an unconfirmed premise.

Same five tests, same file, two agents, two routes. That is enough to stop
calling them uncharacterized.

HYPOTHESIS -- NOT VERIFIED, AND THE INTERESTING PART IS THAT IT IMPLICATES A
FIX RATHER THAN A BUG. T-3230 (landed 27bd2c0bcce3) deliberately changed
archive's live-worktree measurement to FAIL CLOSED. `src/frob/tickets/
_archive.py:276` now returns `TicketError.ArchiveWorktreeMeasurementFailed`
when the worktree list cannot be measured, where the pre-fix code fell through
into silently permitting the archive.

That change is CORRECT and must not be reverted -- an unmeasurable worktree
list previously read as "no live worktrees", which is the silent-zero class and
exactly what T-3230 was filed to kill.

But it means a `git worktree list` that fails under load now produces a REFUSAL
where it previously produced a silent pass. If these tests were passing before
T-3230 by accident -- because the failed measurement degraded to "empty" and
archive proceeded -- then T-3230 converted a latent, invisible defect into five
visible test failures. That is the fix working as designed, and the tests are
now telling the truth about a fragile measurement.

WHAT TO DETERMINE, in this order:
  1. Do these five fail because of the T-3230 refusal path? Check whether the
     failure message names `ArchiveWorktreeMeasurementFailed` or the live-
     worktree refusal, versus failing some other way. If it is neither, this
     whole hypothesis is wrong -- say so and re-triage from the actual error.
  2. Did they pass before T-3230? Check out its parent and run them under the
     same contention. If they passed only because the measurement silently
     degraded, record that plainly -- it is the strongest possible evidence
     that T-3230 was worth doing.
  3. WHY does `git worktree list` exit 128 under load at all? That is the real
     defect underneath. Contention on the git index or worktree metadata is a
     transient, expected condition on a box running several agent fleets; a
     transient git failure should be retried or reported as transient, not
     treated as a permanent unmeasurable state.

DO NOT FIX THIS BY MAKING ARCHIVE FAIL OPEN AGAIN, and do not fix it by marking
the tests flaky or adding a retry decorator to them. Both delete the detector.
If the measurement is genuinely transient, the retry belongs in the MEASUREMENT
(bounded, logged per attempt), not in the test.

SIBLING SURFACE TO CHECK AND REPORT, NOT FIX: T-3230 triaged 37 `git`-spawn
call sites and judged 28 "low-stakes/advisory where the empty-on-failure
direction is already safe". This incident is evidence that at least one such
judgement deserves re-examination under real contention. Report how many of
those 28 sit on a path that can refuse or mutate state; do not re-open them all.

MUST-FIRE FIXTURE: an archive attempt whose `git worktree list` fails is
refused with the unmeasurable error, distinct from a genuine live-worktree
refusal.
MUST-STAY-QUIET FIXTURE: a normal archive in a quiet tree still succeeds, and
the five named tests pass under ordinary conditions.
THIRD FIXTURE: a transient measurement failure that succeeds on retry does not
surface as a refusal at all.

ACCEPTANCE
- A stated answer to (1) and (2) with evidence.
- The transient-versus-permanent distinction made in the measurement, not in
  the tests.
- The five named tests pass under contention, without being marked flaky.
- A stated count for the sibling surface.


CONFOUND WARNING FROM THE COORDINATOR, 2026-08-29. Read this before treating
any current measurement of these five tests as evidence.

INDEPENDENT CORROBORATION FIRST. Series EK re-measured on current main and
reports all five TestArchive tests still failing, with a sharper root-cause
observation than we had:

    the TestArchive::* and gitio worker-lock failures all trace to
    `git worktree list` returning 128 INSIDE PYTEST TMP DIRS

That is a third independent sighting (Series DS's baseline, Series DX in
passing, now Series EK), and the first to locate the failing call inside the
tests' own temporary directories rather than against the real repo.

NOW THE CONFOUND, AND IT IS MINE. While Series EK was mid-measurement I reaped
five stale git worktrees from this repo:

    t-3277, t-3283, t-3303, t-3305, t-3316   (all landed, clean, done)

`git worktree remove` MUTATES the worktree list. A concurrent `git worktree
list` -- which is exactly the call these five tests are failing on -- can
plausibly fail or race while entries are being removed. I do not know whether
the runs overlapped, and I did not check before reaping.

SO: the current failure evidence for these five is CONTAMINATED and must not
be used to conclude anything about the underlying cause. It may be:
  (a) the T-3230 fail-closed path firing on a genuinely transient git failure
      under host contention (the original hypothesis), or
  (b) an artifact of my concurrent worktree removal, or
  (c) both, or
  (d) a real defect independent of either.

WHAT THE RE-MEASUREMENT MUST CONTROL FOR, in this order:
  1. A QUIET BOX. Load was 46-55 on 12 cores during EK's run with 13 concurrent
     `frob check` processes and 61 forkservers. Series EF independently found it
     had to drop to lower `-n` or `-p no:xdist` to get a signal it could believe
     under this same load.
  2. NO CONCURRENT WORKTREE MUTATION. No reaping, no `frob ticket work`, no
     land creating or removing a worktree, for the duration of the run.
  3. Run the five SERIALLY (`-p no:xdist`) so an xdist worker death cannot be
     mistaken for a test failure -- that conflation has already produced a
     false failure list once today.

If they still fail under all three controls, the finding is real and the
original hypothesis stands. If they pass, this ticket is a host-contention
artifact and should be closed as such WITH the controls stated, not quietly
dropped -- a test that only fails under concurrent worktree mutation is still
worth knowing about, because this repo runs many concurrent worktrees by
design.

DO NOT mark these flaky, add retries, or skip them. A load-dependent product
defect and a flaky test look identical from the outside, and this repo's whole
argument is that the difference matters.


ROOT CAUSE FOUND, AND IT IS DETERMINISTIC. 2026-08-29, coordinator. This
supersedes the host-contention hypothesis and clears the contamination warning
recorded above.

MEASUREMENT CONDITIONS, which satisfy the controls this ticket demanded:
  - idle box: load near zero, 21GB free, no other agents running
  - NO concurrent worktree mutation: no reaping, no `frob ticket work`, no land
    creating or removing a worktree for the whole run
  - no coverage instrumentation (which is separately deadlock-prone, T-3420)
  - xdist -n 8, whole top-level slice: collected=6255 failed=8, 203s

Five of those eight failures are this ticket's TestArchive cluster. They fail
every time, not sometimes.

THE ACTUAL MECHANISM, from the captured log of
TestArchive::test_moves_done_and_dropped_only:

    gitio: spawning ('git', '-C', '<pytest tmp_path>', 'worktree', 'list',
                     '--porcelain')
    gitio: ... -> returncode=128
    tickets: git worktree list failed under <pytest tmp_path>
    tickets: archive refused -- could not measure live git worktrees ...
             an unmeasurable read is never treated as 'no live worktrees'
    assert result.is_ok
    E   where False = Err(TicketError.ArchiveWorktreeMeasurementFailed).is_ok

`git worktree list` returns 128 because THE FIXTURE'S tmp_path IS NOT A GIT
REPOSITORY. These tests build a ticket tree in a bare temporary directory and
never run `git init`. Compare tests/system/test_cli_check.py, whose fixtures
call `git_init_and_config(main_repo)` explicitly before exercising anything
git-aware.

So this is not flakiness, not host load, and not the coordinator's concurrent
worktree reaping. Earlier sightings correlated with load only because the whole
suite was being run more often under load.

WHAT IT ACTUALLY IS: a contract change that outran its fixtures. T-3230 made
`archive` FAIL CLOSED on an unmeasurable worktree read -- correct and
deliberate, and the refusal message says exactly why ("an unmeasurable read is
never treated as 'no live worktrees'"). That introduced a new precondition:
archive now requires a working git repository. The TestArchive fixtures predate
that requirement and were never updated, so they exercise archive in an
environment where the precondition cannot hold.

DO NOT FIX THIS BY WEAKENING THE FAIL-CLOSED PATH. Treating a failed
`git worktree list` as "no live worktrees" is precisely the silent-zero defect
this repo keeps finding, and T-3230 exists to prevent it. The guard is right.

THE REAL CHOICE, to be made explicitly:
  (a) `git init` in the TestArchive fixtures so they exercise archive under its
      real precondition. Most faithful; slightly slower fixtures.
  (b) Have the tests pass `--force`, the documented escape the refusal itself
      names. Cheapest, but it means these tests stop covering the default path,
      which is the path users take -- probably wrong for that reason.
  (c) Decide that archive SHOULD tolerate a non-repo directory as a distinct,
      explicitly-detected case (not an unmeasurable read, but a definite "this
      is not a git repo"), and make the code distinguish the two. This is
      arguably the most correct: "the read failed" and "there is no repo here"
      are different facts currently collapsed into one error.
I lean (c) with (a) as the fixture-side companion, because collapsing those two
facts is the same measurement-honesty problem in miniature. State the reasoning
rather than inheriting mine.

WHATEVER IS CHOSEN, the other three failures in this run's slice
(test_docptr_gate, test_ticket_land TestPreCommitUnscopedSweep,
test_ticket_work_and_land_finish TestBranchDriftGuard) are NOT part of this
cluster and must be attributed separately. Do not sweep them in.

MUST-FIRE FIXTURE:   archive against a directory where the worktree read
                     genuinely fails still refuses.
MUST-STAY-QUIET:     archive in a normal repository with no live worktrees
                     succeeds.
THIRD FIXTURE:       if (c) is chosen, a non-repo directory is reported as a
                     distinct condition from an unmeasurable read.

ACCEPTANCE
- The chosen option stated with reasoning.
- All five TestArchive tests passing, measured on a quiet box with no
  concurrent worktree mutation, with the before/after numbers stated.
- The fail-closed behaviour still present and proven by the must-fire fixture.
