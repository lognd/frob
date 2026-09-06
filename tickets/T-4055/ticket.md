---
id: T-4055
title: 'Ubuntu CI fails exactly one DIFFERENT test per run: a load-sensitive flake
  population makes green unreachable by chance'
state: in-progress
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_serve_socket.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: add full CI-mined enumeration, classification and cross-platform correction
    ahead of the Done report
  actor: logan
  at: '2026-09-06'
  old_length: 3802
  new_length: 9351
evidence:
- tests/test_serve_socket.py::TestRunSocketDaemon::test_serves_one_request_then_idle_exits
- tests/test_serve_socket.py::TestRunSocketDaemon::test_stale_socket_file_is_replaced
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
UBUNTU HAS FAILED EXACTLY ONE TEST ON EACH OF THREE CONSECUTIVE RUNS, AND IT IS A
DIFFERENT TEST EVERY TIME. That pattern -- not any individual failure -- is the
defect.

MEASURED, three consecutive CI runs on main:
  ca586645c  tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring
             ::test_capability_conformance_fires_through_real_gate_dispatch
             -> IndexError from an empty sqlite row (fixed, T-4018/T-4047)
  78f511af0  tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI
             ::test_force_with_no_live_leases_stays_quiet
  c25ca1573  tests/test_serve_socket.py::TestRunSocketDaemon
             ::test_serves_one_request_then_idle_exits
             -> thread still alive after join(timeout=5)

Each run: 13500-ish collected, exactly 1 failed. None repeated. macOS on the same
commits is GREEN with the identical suite.

WHY THIS MATTERS FOR THE ALPHA MORE THAN ANY SINGLE FAILURE: at roughly one
flake per run, ubuntu will essentially NEVER be green by chance. "Full CI green
before the alpha" is therefore not reachable by fixing the currently-visible
failure -- fix it and the next run surfaces a different one. THE POPULATION IS
THE BLOCKER, not its current member.

THE COMMON SHAPE IS TIME AND CONCURRENCY, not logic. The newest instance is
explicit about it:

    cfg = SocketDaemonConfig(root=root, idle_timeout_s=0.3)
    ...
    thread.join(timeout=5)
    assert not thread.is_alive()

A daemon configured to idle out in 0.3s, given 5s to die, under an xdist run of
13507 tests on a shared CI runner. That is not a correctness assertion; it is a
bet on scheduling. The T-4018 instance was likewise concurrency-dependent (it
failed on gw1 in a full run and PASSED when I ran it alone).

WHAT TO DO -- and the first step is measurement, not fixes:
1. ENUMERATE THE POPULATION. Re-run the suite on ubuntu N times (or mine recent
   CI history) and collect every test that has failed at least once while passing
   on other runs. The deliverable is a LIST, because we currently have three
   samples of an unknown-size set and no idea whether it is 5 tests or 50.
2. CLASSIFY EACH by mechanism: a wall-clock bet (join/sleep/timeout), a shared
   resource under xdist, or genuine order-dependence. The remedies differ and
   lumping them produces bad fixes.
3. ONLY THEN fix. For wall-clock bets prefer waiting on the CONDITION with a
   generous cap over asserting a fixed deadline -- `assert not thread.is_alive()`
   after a fixed join is the anti-pattern; polling until dead-or-deadline with a
   much larger deadline tests the same property without betting on the scheduler.

DO NOT fix this with retries or reruns. A rerun-until-green policy converts a
flake into an invisible flake, and this repo already treats "the failing set is
incomplete" as a first-class defect. The suite should be deterministic, not
retried.
DO NOT mark them xfail or skip. Same reason as the Windows work: in a CI summary
an xfail is indistinguishable from a fix.

NOTE macOS IS GREEN ON THE SAME COMMITS. That is useful evidence: the tests are
not wrong in general, and the ubuntu runner's timing/parallelism is a real
variable. Check whether the ubuntu leg runs a different xdist worker count or
under different load than macOS -- if so, that asymmetry is a lead, not a
coincidence.

MUST-FIRE FIXTURE: a genuinely broken daemon (never exits) still fails the test.
MUST-STAY-QUIET: the daemon test passes reliably under a loaded parallel run --
demonstrated by repetition, not by a single green run.

ACCEPTANCE
- An enumerated list of load-sensitive tests, with the sampling method stated.
- Each classified by mechanism before any fix.
- No retries, xfails or skips used to reach green.
- Both fixtures committed for at least the daemon case.

Changed:
tests/test_serve_socket.py::TestRunSocketDaemon.test_serves_one_request_then_idle_exits
tests/test_serve_socket.py::TestRunSocketDaemon.test_stale_socket_file_is_replaced

ENUMERATION (primary deliverable). Method: `gh api repos/{owner}/{repo}/actions/jobs/<id>/logs`
against the ubuntu-latest job of the 23 most recent CI runs on main (push and
pull_request, both failure and success conclusions, 2026-09-03 through
2026-09-06), grepping the SUITE-RESULT/SUITE-RESULT-FAILED markers
tests/conftest.py already emits. This supersedes the ticket's own 3-sample
premise -- the population is at least 6 distinct tests, not 3:

  TRUE single-run intermittent failures (different test each occurrence,
  passes on adjacent commits -- same population this ticket targets):
    tests/test_serve_socket.py::TestRunSocketDaemon::test_serves_one_request_then_idle_exits   (run c25ca1573/34030362843)
    tests/test_serve_socket.py::TestRunSocketDaemon::test_stale_socket_file_is_replaced         (run 33739420656)
    tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring::test_capability_conformance_fires_through_real_gate_dispatch  (run ca586645c/34019760758; already fixed, T-4018/T-4047)
    tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal      (run 34019848542)
    tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_with_no_live_leases_stays_quiet       (run 78f511af0/34024645783)
    tests/test_check_runner.py::TestApplyTierAAndReverify::test_ticket_scoped_fix_never_touches_files_outside_declared_scope (run 33890430001)
    tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta (macOS, run 5e1eebf79, per coordinator correction -- cross-platform, not ubuntu-specific)

  NOT YET CLASSIFIED (only sampled from log text, flagged not fixed):
    7 tests in tests/unit/test_check_tool_unavailable.py failed TOGETHER in one
    run (33945397250) -- shape points at a shared xdist resource, not
    independent wall-clock bets.

  SEPARATELY (not part of this population -- a real bug fixed by a later
  commit, not scheduler-driven): tests/system/test_artifact_smoke.py (x2),
  tests/test_docptr_gate.py, tests/test_ticket_land_proof_claims.py (x6)
  failed IDENTICALLY across 5 consecutive ubuntu runs (34005559354 ..
  34013571660) then stopped appearing entirely from 34019760758 onward.

CROSS-PLATFORM CORRECTION (from coordinator, addressed): macOS is not reliably
green either -- CI run 5e1eebf79 failed
tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta
("Cannot operate on a closed database") after the immediately preceding
commit was green. Ruled out as a T-4018/T-4047 regression (the guard those
tickets touched, `_warn_if_empty_row`, is pure logging over an already-read
row and never touches the connection/cursor) and reproduced clean locally (9
collected, 0 failed) by the coordinator -- genuine flake, category (b) shared
sqlite connection under concurrency, added to the population above. This test
is in tests/unit/test_graph_cache.py, outside T-4055's declared scope
(tests/test_serve_socket.py); not fixed here, left for the filed follow-up.

CLASSIFICATION of the two tests fixed in this ticket's scope:
  Category (a), WALL-CLOCK BET. Both tests configured
  `SocketDaemonConfig(idle_timeout_s=0.3)`, then asserted
  `not thread.is_alive()` immediately after a single `thread.join(timeout=5)`.
  Under xdist load (13500+ tests collected) the daemon's idle-timeout poll
  loop is not always scheduled inside that 5s window, so the assertion fires
  even though the daemon would die shortly after. Not a shared-resource or
  order-dependence failure -- each test uses its own `root` tmp_path fixture
  and its own daemon thread.

FIX: replaced the fixed join+assert with poll-until-dead-or-30s-deadline in
both tests (`while thread.is_alive() and time.monotonic() < deadline:
thread.join(timeout=0.1)`) -- tests the same property (the daemon does
eventually exit) without betting on the scheduler; a daemon that never exits
still fails loudly (MUST-FIRE preserved). Also removed
test_stale_socket_file_is_replaced's `@pytest.mark.flaky(reruns=2,
reruns_delay=1)` marker, which was masking the identical nondeterminism via
reruns -- prohibited by this ticket's own "no retries" rule, and by this
repo's own T-3775 doctrine (flakes are fixed, not rerun around).

Verification (MUST-STAY-QUIET, demonstrated by repetition, not one green
run): 15/15 clean runs of `pytest -n 4 --dist=loadgroup
tests/test_serve_socket.py::TestRunSocketDaemon` in isolation, plus 4/6 clean
runs (2 timed out on an unrelated slow test_graph_cache case at the 90s
harness timeout, not on the daemon tests) of a wider 3-file xdist run
(tests/test_serve_socket.py + tests/test_ticket_leases.py +
tests/unit/test_graph_cache.py) for background load, all on this machine
forced to -n 4 to match ubuntu-latest's real worker count (ubuntu-latest has
4 vCPUs vs. this machine's 12; pyproject.toml addopts is `-n auto`, so CI's
own worker count differs by runner, not by explicit config divergence between
the ubuntu and macOS legs -- both legs run the identical `-n auto
--dist=loadgroup` addopts, so the macOS/ubuntu asymmetry lead did not pan out
as a config difference, consistent with the coordinator's correction that
macOS now flakes too).

