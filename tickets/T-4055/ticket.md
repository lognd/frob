---
id: T-4055
title: 'Ubuntu CI fails exactly one DIFFERENT test per run: a load-sensitive flake
  population makes green unreachable by chance'
state: queued
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