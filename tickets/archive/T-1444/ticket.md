---
id: T-1444
title: Wire merge-queue enqueue/drain into frob ticket land CLI
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/**
- src/frob/app/ticket_runner/**
- docs/modules/tickets.md
- src/frob/tickets/_models.py
- tests/test_ticket_land.py
- tests/unit/test_land_queue.py
- tests/unit/test_ticket_runner_land_cmd_flags.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'The drain loop''s land_fn (frob.tickets._land_queue.drain_next''s own

    contract) must return Result[LandReport, LandError] so a failing

    ticket''s own failure mode is attributable, matching this ticket''s own

    acceptance criterion ("a failing ticket is named and dequeued alone").

    The existing post-land unscoped-error-sweep revert path

    (_post_land_unscoped_error_sweep / _run_post_land_sweep_or_exit) has no

    LandError member today -- it calls sys.exit(1) directly, which is fine

    for a single interactive `frob ticket land` call but would kill the

    whole drain loop on one ticket''s revert. A new PostLandUnscopedSweepFailed

    LandError member (frob/tickets/_models.py) is the minimal, necessary

    addition to make that failure mode returnable instead of process-exiting.

    '
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'Need test coverage for the new frob ticket land --queue/--drain CLI

    paths (_land_enqueue/_land_drain/_land_core in

    src/frob/app/ticket_runner/_land_cmd.py) and the new LandError member

    (PostLandUnscopedSweepFailed). tests/test_ticket_land.py is the existing

    home for CLI-level land tests; tests/unit/test_land_queue.py already

    covers frob.tickets._land_queue directly and is the natural place for

    any queue-level assertions this ticket''s CLI wiring needs.

    '
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/unit/test_land_queue.py
  reason: 'Need test coverage for the new frob ticket land --queue/--drain CLI

    paths (_land_enqueue/_land_drain/_land_core in

    src/frob/app/ticket_runner/_land_cmd.py) and the new LandError member

    (PostLandUnscopedSweepFailed). tests/test_ticket_land.py is the existing

    home for CLI-level land tests; tests/unit/test_land_queue.py already

    covers frob.tickets._land_queue directly and is the natural place for

    any queue-level assertions this ticket''s CLI wiring needs.

    '
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/unit/test_ticket_runner_land_cmd_flags.py
  reason: 'tests/unit/test_ticket_runner_land_cmd_flags.py is the established

    parser->AppConfig->_land_cmd wiring-pin pattern (T-1369''s own precedent,

    its module docstring: "pin the whole path... every previous break in

    this chain was a wiring gap, not a logic bug") -- the natural home for

    --queue/--drain''s own parser->config->dispatch pin tests, same shape as

    the file''s existing --allow-cross-ticket tests.

    '
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainFlagParsing::test_queue_flag_sets_the_namespace_dest
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainFlagParsing::test_drain_flag_sets_the_namespace_dest
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainFlagParsing::test_absent_flags_default_false
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainReachesConfig::test_from_external_carries_queue
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainReachesConfig::test_from_external_carries_drain
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDispatchesToQueueOrDrain::test_queue_flag_calls_land_enqueue_not_land_core
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDispatchesToQueueOrDrain::test_drain_flag_calls_land_drain_not_require_land_args
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandEnqueue::test_enqueue_success_reaches_land_queue_enqueue
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandEnqueue::test_enqueue_failure_exits_nonzero
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDrain::test_empty_queue_drains_zero_and_returns
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDrain::test_two_entries_call_land_core_per_entry_with_its_own_ticket_id
designated_repro_test: null
acceptance:
- text: 'GIVEN a merge-queue drain of N tickets WHEN it runs THEN exactly one pre-drain
    baseline capture and one post-drain full sweep execute, each queued ticket is
    validated by a per-ticket delta check against the running merge state (attribution
    preserved: a failing ticket is named and dequeued alone, the rest of the batch
    proceeds), and total verification wall-clock for the batch is sublinear in N'
  evidence:
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainFlagParsing::test_queue_flag_sets_the_namespace_dest
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainFlagParsing::test_drain_flag_sets_the_namespace_dest
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainFlagParsing::test_absent_flags_default_false
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainReachesConfig::test_from_external_carries_queue
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestQueueDrainReachesConfig::test_from_external_carries_drain
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDispatchesToQueueOrDrain::test_queue_flag_calls_land_enqueue_not_land_core
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDispatchesToQueueOrDrain::test_drain_flag_calls_land_drain_not_require_land_args
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandEnqueue::test_enqueue_success_reaches_land_queue_enqueue
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandEnqueue::test_enqueue_failure_exits_nonzero
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDrain::test_empty_queue_drains_zero_and_returns
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDrain::test_two_entries_call_land_core_per_entry_with_its_own_ticket_id
threat: null
component: null
---
Found while working T-1345 (merge queue: agents enqueue verified
branches, one drainer merges onto main).

T-1345 delivered the queue data structure and library-level API
(frob.tickets._land_queue: enqueue/drain_next/queue_status, backed by
.frob/land-queue.json under its own fcntl lock, tested in
tests/unit/test_land_queue.py) but deliberately stopped short of any CLI
surface, because that needs files outside T-1345's declared scope
(src/frob/tickets/**, docs/modules/tickets.md,
docs/guides/agent-playbook.md):

1. <!-- frob:waive DOC006 reason="ticket plan naming a CLI flag that does not exist yet -- disclosed future work for this ticket to build" -->`frob ticket land --queue` -- enqueue instead of landing immediately.
   Needs a new argparse flag in src/frob/_cli_parsers/_ticket.py (or
   wherever the land subparser lives) and a branch in
   src/frob/app/ticket_runner.py's `_land` command handler that calls
   `frob.tickets._land_queue.enqueue(root, ticket_id, worktree, branch)`
   instead of `frob.tickets.land(...)` directly, then prints the queue
   position and returns 0 immediately (no waiting).

2. A drainer subcommand (e.g. <!-- frob:waive DOC006 reason="ticket plan naming a subcommand/flag that does not exist yet -- disclosed future work for this ticket to build" -->`frob ticket queue drain` or `frob ticket
   land --drain`) that loops `frob.tickets._land_queue.drain_next(root,
   land_fn)` where `land_fn` is a closure calling the real
   `frob.tickets.land(...)` with every callback `ticket_runner.py`'s
   existing `_land` command already supplies (bump_version,
   rebuild_natives, sync_gate_rules, check_gates, etc. -- see
   `land()`'s own docstring for the full list). Must print the SAME
   `LAND-PROOF:` line a normal `frob ticket land` call prints today, from
   the `LandReport` inside `land_fn`'s own `Result` -- the acceptance
   criterion T-1345's ticket body named explicitly ("Preserve the
   existing LAND-PROOF contract").

3. Consider whether the drainer should be a long-running loop (poll the
   queue, drain whenever non-empty, exit on empty or on a signal) or a
   single "drain one and exit" invocation a coordinator calls repeatedly
   (e.g. from a cron-like <!-- frob:waive DOC006 reason="ticket plan naming a hypothetical pattern/subcommand that does not exist yet -- disclosed future work" -->`frob loop` pattern) -- T-1345's own body did
   not specify this and it is a real design choice with different
   operational implications (a long-running loop needs its own
   lifecycle/PID-file story; a single-shot call composes with existing
   external schedulers but needs something to invoke it repeatedly).

4. Docs: docs/modules/tickets.md's new "Merge queue (T-1345, first
   portion)" section needs a follow-up "second portion" edit once the CLI
   verbs exist, replacing the "no CLI surface yet" disclosure with the
   real command reference.

The underlying library code (frob.tickets._land_queue) needs no changes
for this follow-up -- it was designed exactly for this: `land_fn` as an
injected callable is the seam the CLI layer plugs into.