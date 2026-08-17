---
id: T-2155
title: 'land.lock is never reclaimed when its holder dies: a dead pid deadlocked 4
  concurrent lands for 25 minutes and presented as extreme contention'
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_lock_liveness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_lock_liveness.py
  reason: regression-lock test for land.lock SIGKILL self-heal via OS flock, mirroring
    TestSigkillMidStaging's fork-based pattern; new file, avoids the T-2114/T-2118
    lease on tests/test_ticket_land.py
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_land_lock_liveness.py::TestLandLockSurvivesSigkilledHolder::test_land_lock_reclaims_promptly_after_sigkill
- tests/unit/test_land_lock_liveness.py::TestRefuseIfLandInProgressSurvivesSigkilledHolder::test_refuse_if_land_in_progress_clears_promptly_after_sigkill
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

**Finding: the core mechanism this ticket asks for already exists and is already correct.** `_land_lock` (`src/frob/tickets/_land.py`) and `refuse_if_land_in_progress`/`_land_flock_probe` (`src/frob/tickets/_leases.py`) already gate exclusively on a real, non-blocking `fcntl.flock(fd, LOCK_EX | LOCK_NB)` acquisition -- landed by T-1619/T-1634/T-1961/T-2023, well before this ticket was filed. The recorded pid/session_id/started_at JSON in `.frob/land.lock` is used ONLY for (a) a blocked caller's diagnostic log line and (b) `frob doctor`'s `LiveLandProcess` report (`_probe_land_lock_pid_liveness`) -- never to decide whether a fresh acquisition may proceed. `_land_lock`'s own docstring (T-1634) already states the exact invariant the ticket asks for: "The dead holder's `flock` was already released by the kernel the instant that process exited, so nothing is actually blocked; the next real `_land_lock` acquisition self-heals."

I verified this empirically, not just by reading: forked a real child process (`multiprocessing.get_context("fork")`, mirroring `TestSigkillMidStaging`'s own precedent and rationale -- an in-process simulation cannot exercise a real held-then-orphaned OS lock), had it acquire `_land_lock`, `SIGKILL`ed it, confirmed `/proc/<pid>` gone, then measured both a fresh `_land_lock` acquisition and a fresh `refuse_if_land_in_progress` call. Both cleared in under 5ms -- nowhere near the 1509s/25-minute stall the incident measured.

I could not reproduce the incident's actual failure mode against current `main`, so I did not implement a "fix" for a bug that doesn't reproduce in this code today (per the dispatch brief's own instruction: state this plainly rather than force a workaround). What the incident's own "how it presented" section actually pinpoints as the real, still-open gap is diagnostic, not mechanical: nothing surfaces land.lock holder liveness where a coordinator already looks. `frob doctor` already computes exactly that (`LiveLandProcess.alive`), but `scripts/fleet_status.py` -- the dashboard the human was actually reading during the 25-minute stall -- prints nothing about it. That surfacing work was scoped and held by another in-progress ticket (T-2133, leasing `scripts/fleet_status.py` + `tests/unit/test_coordinator_scripts.py` + `docs/guides/coordinator-scripts.md`) -- confirmed via the live cross-worktree lease file at the time, so I did not duplicate it or file a new ticket for it. T-2133 has since landed that surfacing (`6327abd122a7`).

Cross-checked with the coordinator mid-ticket after it flagged a possible collision with T-2157 (staged-root liveness, a different artifact). Replied with this same finding: T-2155 needed zero new liveness code, so there was nothing to coordinate a shared primitive for on the `_land.py`/`_leases.py` side; T-2157 is free to pick whichever existing primitive (`_pid_alive` in `mutate/_journal.py`, or T-1619's `os.kill(pid,0)`-plus-`/proc`-cwd scan) fits its own artifact, or use `_land_lock`'s flock-as-source-of-truth shape as precedent for its own marker file if a flock-based design also fits there.

Changed: tests/unit/test_land_lock_liveness.py (new file)
  - `_child_hold_lock`, `_spawn_and_kill_holder`: fork+SIGKILL harness, mirrors `TestSigkillMidStaging`'s pattern
  - `TestLandLockSurvivesSigkilledHolder.test_land_lock_reclaims_promptly_after_sigkill`
  - `TestRefuseIfLandInProgressSurvivesSigkilledHolder.test_refuse_if_land_in_progress_clears_promptly_after_sigkill`

No changes to src/frob/tickets/_land.py -- investigated in depth, found the mechanism already correct, declined to force a change onto working code.

Evidence:
  tests/unit/test_land_lock_liveness.py::TestLandLockSurvivesSigkilledHolder::test_land_lock_reclaims_promptly_after_sigkill
  tests/unit/test_land_lock_liveness.py::TestRefuseIfLandInProgressSurvivesSigkilledHolder::test_refuse_if_land_in_progress_clears_promptly_after_sigkill
  (2 passed; `SUITE-RESULT: exitstatus=0 collected=2 failed=0`)

Not designated as a BUG002 repro: `--check-repro` correctly reports `TEST_ABSENT_AT_PARENT` against the merge-base (the file is new, and per T-2025 no ref in this repo's history ever contains a new test without its "fix" already applied) -- and more fundamentally, neither test fails against current `main` at all, so there is no repro to designate. This ticket closes as "investigated, mechanism already correct, no fix needed" rather than "bug fixed."

Filed: none -- the one adjacent, genuinely-open gap (fleet_status.py surfacing) is already covered by T-2133's live lease; filing a duplicate would violate the "search the code, not just the queue" rule.

Gates: `frob check --land-parity` clean (0 unscoped errors). `frob check --ticket T-2155` scoped run: WIRE001/FMT001/PRE001 findings from the first pass were all fixed (waiver + `frob fmt` + a fresh `frob ticket sweep`); remaining FAIL lines (`gate:TICK` TICK003/004/007 backlog rot, `gate:SELFAUDIT` SYS100/SYS111 via-list/ratchet sync) are repo-wide, pre-existing, and per this repo's own convention (`fix_sys100_may_via_union`/`fix_sys111_capability_ratchet_sync`, both registered Tier-A auto-fix handlers) are synced automatically by `frob ticket land` itself before its own merge -- not hand-edited here, per the coordinator's explicit note not to touch `capability-via-ratchet.lock.json` by hand.

### Changed
```
 tests/unit/test_land_lock_liveness.py | 154 ++++++++++++++++++++++++++++++++++
 tickets/T-2155/done-report.md         |  43 ++++++++++
 tickets/T-2155/ticket.md              |  14 +++-
 3 files changed, 210 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_land_lock_liveness.py::TestLandLockSurvivesSigkilledHolder::test_land_lock_reclaims_promptly_after_sigkill` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_lock_liveness.py::TestRefuseIfLandInProgressSurvivesSigkilledHolder::test_refuse_if_land_in_progress_clears_promptly_after_sigkill` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: SELFAUDIT001@design, TICK004@tickets.md
