---
id: T-3643
title: xdist-only pytest_testnodedown hook kills Windows suite (-p no:xdist)
state: queued
kind: bug
origin: human
created: '2026-09-01'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- tests/unit/test_conftest_stackdump.py
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
Run 33491468339 windows Test step: SUITE-RESULT: DID-NOT-COMPLETE exitstatus=3 (INTERNAL-ERROR) collected=0, cause=PluginValidationError: unknown hook 'pytest_testnodedown' in plugin tests.conftest.

T-3608's stall watchdog added the xdist-only hook pytest_testnodedown to tests/conftest.py. The Windows Test step runs -p no:xdist, so pytest refuses to start AT ALL there. Fix: mark the hook optional -- @pytest.hookimpl(optionalhook=True) on pytest_testnodedown (matching the existing pattern on pytest_handlecrashitem in the same file) -- audit for any other xdist-only hooks in this file missing the decorator. Verify: pytest -p no:xdist --collect-only -q succeeds locally, AND the watchdog tests still pass with xdist enabled.

NOTE: the watchdog itself worked perfectly on both POSIX legs this run (loud STALL-DETECTED abort in ~4 min instead of a 40-min budget burn) -- do not weaken it, just make the hook declaration xdist-optional.