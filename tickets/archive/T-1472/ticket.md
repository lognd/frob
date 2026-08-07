---
id: T-1472
title: Capture kernel OOM evidence for make-coverage worker deaths + broaden T-1433
  xdist_group allowlist
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- tests/system/test_frob_self_model.py
- tests/unit/strata/test_selfconform.py
- tests/conftest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group
designated_repro_test: null
threat: null
component: null
---
Found while working T-1433 (drain-to-zero wedge investigation).

T-1433 root-caused "node down: Not properly terminated" xdist worker
deaths in `make coverage` to a LEADING theory (kernel OOM-kill: no
faulthandler fault trace near the node-down line rules out a caught
SIGSEGV/SIGABRT, matching this host's own documented WSL OOM-kill
history and the Makefile's T-1353 memory-pressure finding) but could not
capture a smoking-gun kernel log line naming the killed PID -- `dmesg`/
`journalctl -k` show no OOM entries on this host right now (buffer
rotated since the reproductions).

Two follow-ups:

1. Wire direct OOM evidence capture into the `make coverage` recipe (or
   a wrapper around it) -- e.g. a background `dmesg -w`/`journalctl -kf`
   tail redirected to a file for the duration of the xdist phase, or
   per-worker `resource.setrlimit`/cgroup memory accounting -- so the
   NEXT reproduction captures the kernel's own kill reason directly
   instead of inferring it from absence of a fault trace.

2. T-1433's `xdist_group` mitigation (tests/conftest.py's
   `pytest_collection_modifyitems`) only groups the 3 self-scan tests it
   could name from inside its own declared scope
   (`test_sys_gate_zero_violations`,
   `test_repo_design_and_declarations_are_self_conformant`,
   `test_repo_unrestricted_scan_is_clean`). A grep during that
   investigation found several MORE full-repo-scan-shaped tests outside
   its scope: tests/test_registry_reconciliation_*.py,
   tests/test_check_coverage_registry.py, tests/test_waive_gate.py,
   tests/test_excludes.py, tests/test_coverage.py,
   tests/unit/strata/test_system_design_coverage.py. Audit which of
   these are genuinely full-repo (`_REPO_ROOT`-scoped) scans as heavy as
   the three already grouped, and extend the `xdist_group` allowlist (or
   the underlying heuristic) to cover them too.