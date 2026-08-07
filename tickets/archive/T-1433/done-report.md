## Done report

Final causal chain, established across four instrumented reproductions
on 2026-08-02/03:

1. At COVERAGE_WORKERS=4 on this 4-core WSL box, one coverage-traced
   xdist worker is reproducibly killed by an uncatchable signal
   (OOM-shaped: no faulthandler trace despite faulthandler being
   enabled, "node down: Not properly terminated", kill point varies
   from 21 percent to 99 percent of the run -- systemic memory
   pressure, not one heavy test).
2. After the death, pytest-xdist's scheduler deadlocks: SIGUSR1 stack
   dumps (tests/conftest.py instrumentation built by this ticket) show
   the master parked in dsession.loop_once queue.get and every
   surviving worker parked in remote.run_one_test waiting for the next
   command -- a protocol deadlock, no lock involved.

Delivered by this ticket across its sessions: the serial-rerun timeout
bound; the xdist-phase COVERAGE_XDIST_DEADLINE bound; SIGUSR1
all-thread stack-dump instrumentation (FROB_COVERAGE_STACKDUMP=1) plus
faulthandler_timeout; xdist_group serialization of the three known
full-repo self-scan tests; and the operational fix -- COVERAGE_WORKERS
defaults to 2, the measured-safe width (the 2026-08-03 2-worker run
completed with zero worker deaths, the first clean completion after
four consecutive 4-worker wedges).

Remainder is tracked, not lost: T-1472 (capture direct kernel OOM
evidence; broaden the heavy-test allowlist) stays the follow-up for
proving the kill mechanism at the kernel level and for any future
attempt to raise the width back to 4.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_makefile_coverage.py::TestSerialRerunHasABoundedDeadline::test_both_serial_reruns_are_wrapped_in_a_bounded_timeout` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestSerialRerunHasABoundedDeadline::test_timeout_wrapping_kills_a_wedged_child_instead_of_hanging` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 2134 warning(s), 740 waived
- error-findings: none (measured, zero errors)
