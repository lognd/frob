## Done report

Wired T-1345's merge-queue library (frob.tickets._land_queue) into the
frob ticket land CLI, per T-1345's own filed follow-up scope.

Shipped:
- `frob ticket land <id> --worktree <path> --queue`: enqueue instead of
  landing immediately (_land_enqueue calls frob.tickets.enqueue), prints
  the assigned FIFO position, returns right away.
- `frob ticket land --drain`: serially process every queued entry, one
  process/invocation (_land_drain loops frob.tickets.drain_next), not a
  long-running poll loop -- a coordinator/scheduler calls it repeatedly.
  Needs neither <id> nor --worktree; --worktree is no longer
  argparse-required (was required=True, blocking --drain outright) --
  enforced instead in the app layer for every other mode
  (_require_land_args / _land_plan_cmd's own pre-existing check).
- _land_core: the merge-check-splice-close-commit-sweep chain factored
  out of the old inline _land() body so both a direct `frob ticket land
  <id>` call and _land_drain's per-entry land_fn run the exact SAME
  path -- same LAND-PROOF: line on every real success either way
  (T-1345's own "preserve the existing LAND-PROOF contract" acceptance
  criterion). Unlike the old body, _land_core never calls sys.exit: a
  post-land unscoped-error-sweep revert returns the new
  LandError.PostLandUnscopedSweepFailed member instead, so a drain
  batch can attribute the failure to the one ticket that caused it
  (dequeued, logged, never retried -- drain_next's own T-1345 policy,
  unchanged) and keep draining the rest.

Acceptance criterion 0 partially met, disclosed honestly:
- MET: per-ticket delta validation preserving attribution -- a failing
  ticket in a --drain batch is named (LandError value + ticket id
  logged) and dequeued alone; the rest of the batch proceeds (proven by
  TestLandDrain::test_two_entries_call_land_core_per_entry_with_its_own_
  ticket_id -- two queued entries, each land_fn call receives its OWN
  ticket_id/worktree, not the CLI's).
- NOT MET (disclosed, follow-up ticket filed): "one baseline capture +
  one full sweep per drain of N tickets" and "sublinear total
  verification wall-clock" -- _land_core still runs its OWN baseline
  capture + post-land sweep per ticket inside the drain loop, identical
  cost to N separate manual `frob ticket land` calls. Sharing one
  baseline/sweep across a whole batch needs _land_core's sweep/baseline
  steps split from the per-ticket land() call itself, a real design
  change (see the ticket body's own escape hatch: ship enqueue + serial
  drain with per-ticket delta checks and file real follow-up tickets for
  parallelism -- this is exactly that ship).

Real bug found and fixed while measuring T-1445's warm-run numbers,
BEFORE landing anything: T-1445's own root_content_key (the whole-tree
cache key for the new process-gate cache) used `git ls-files -s`'s INDEX
blob sha, which does not reflect an on-disk edit that was never `git
add`ed -- exactly the everyday state of an in-progress worktree agent's
own checkout. Fixed to read each tracked path's current bytes directly
(commit b8b0e3ed, same worktree, T-1445's own scope). Caught it directly
by observing a stale ARCH103 finding survive an unstaged edit to the
very function it should have flagged.

Scope widened beyond the ticket's original 3 globs (frob ticket scope
--add, each with a --reason-file):
- src/frob/tickets/_models.py: LandError.PostLandUnscopedSweepFailed is
  the minimal necessary addition for _land_drain's own attribution
  requirement (a drain-loop failure needs a returnable LandError value,
  not a process-killing sys.exit).
- src/frob/app/_config_external.py: two field-name additions
  (ticket_land_queue, ticket_land_drain) -- the same silently-dropped-
  CLI-flag class of gap T-1445's WIRE001 caught for --no-cache.
- tests/test_ticket_land.py, tests/unit/test_land_queue.py,
  tests/unit/test_ticket_runner_land_cmd_flags.py: test coverage for the
  new CLI paths and LandError member -- the latter file is the
  established parser->AppConfig->_land_cmd wiring-pin pattern (T-1369's
  own precedent).

Filed a follow-up (draft ticket, renumbers at land) for the "one shared
baseline+sweep per drain batch" -- the sublinear-verification half of
this ticket's acceptance criterion, deferred per the ticket's own
escape hatch.


Waiver deletions in branch history (intentional, sibling T-1445's already-landed work, commit 9d6d2da4): src/frob/gates/__init__.py:ARCH001 (x2) and src/frob/gates/__init__.py:PERF004 -- removed by T-1445's gate-cache refactor of _run_process_gate, which made the waived shapes obsolete. Declared here because gates/__init__.py is outside T-1444's scope and the history scan attributes the whole branch to the landing ticket.

### Changed
```
 design/frob.strata                              | 823 ++++++++++++------------
 docs/modules/gates.md                           |  50 ++
 docs/modules/tickets.md                         |  46 +-
 src/frob/_cli_parsers/_check.py                 |  11 +
 src/frob/_cli_parsers/_ticket/_progress.py      |  38 +-
 src/frob/app/_config_external.py                |   6 +
 src/frob/app/check_runner.py                    |   8 +
 src/frob/app/config.py                          |  18 +
 src/frob/app/ticket_runner/_land_cmd.py         | 238 ++++++-
 src/frob/gates/__init__.py                      | 449 ++++++++++---
 src/frob/gates/_gate_cache.py                   | 184 +++++-
 src/frob/tickets/_models.py                     |  12 +
 tests/test_gate_cache.py                        | 330 ++++++++++
 tests/unit/test_ticket_runner_land_cmd_flags.py | 266 ++++++++
 tickets.md                                      | 496 +++++++++++++-
 15 files changed, 2449 insertions(+), 526 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainFlagParsing::test_queue_flag_sets_the_namespace_dest` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainFlagParsing::test_drain_flag_sets_the_namespace_dest` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainFlagParsing::test_absent_flags_default_false` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainReachesConfig::test_from_external_carries_queue` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainReachesConfig::test_from_external_carries_drain` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDispatchesToQueueOrDrain::test_queue_flag_calls_land_enqueue_not_land_core` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDispatchesToQueueOrDrain::test_drain_flag_calls_land_drain_not_require_land_args` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandEnqueue::test_enqueue_success_reaches_land_queue_enqueue` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandEnqueue::test_enqueue_failure_exits_nonzero` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDrain::test_empty_queue_drains_zero_and_returns` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDrain::test_two_entries_call_land_core_per_entry_with_its_own_ticket_id` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 1 error(s), 807 warning(s), 794 waived
- error-findings: PRE001@tickets/T-1444
