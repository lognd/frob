---
id: T-1823
title: wire frob serve daemon / check subprocess pool into the SIGUSR1 stack-dump
  handler
state: done
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/serve/server.py
- tests/test_serve.py
- src/frob/serve/_daemon.py
- src/frob/testing/_stackdump.py
- docs/modules/serve.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/serve/**
  reason: SIGUSR1 stackdump wiring only needs run_stdio (the process entry point that
    actually starts the daemon thread and blocks) in src/frob/serve/server.py; the
    rest of src/frob/serve/** (socketd, watch, leases, events, tools) has no relevant
    entry point for this ticket
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/serve/server.py
  reason: SIGUSR1 stackdump wiring only needs run_stdio (the process entry point that
    actually starts the daemon thread and blocks) in src/frob/serve/server.py; the
    rest of src/frob/serve/** (socketd, watch, leases, events, tools) has no relevant
    entry point for this ticket
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_serve.py
  reason: SIGUSR1 stackdump wiring only needs run_stdio (the process entry point that
    actually starts the daemon thread and blocks) in src/frob/serve/server.py; the
    rest of src/frob/serve/** (socketd, watch, leases, events, tools) has no relevant
    entry point for this ticket
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/serve/_daemon.py
  reason: run_stdio genuinely calls _start_daemon (src/frob/serve/_daemon.py) directly
    -- scope-closure under-capture warning
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/testing/_stackdump.py
  reason: T-1823's wiring makes the two frob:waive WIRE001 follow_up=T-1823 waivers
    here stale (a real non-test caller now exists) -- removing the now-unneeded waivers
    and re-pointing away from T-1823 is required so closing T-1823 does not orphan
    a still-live citation (LiveTrackerCited)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/serve.md
  reason: 'AFFECT001: run_stdio''s doc anchor docs/modules/serve.md#mcp-sdk needs
    the SIGUSR1 stackdump wiring mentioned'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_serve.py::TestBuildServer::test_run_stdio_installs_stackdump_handler_before_serving
- tests/unit/test_stackdump.py::TestStackdumpHandler::test_sigusr1_writes_all_thread_stacks_when_enabled
- tests/unit/test_stackdump.py::TestStackdumpHandler::test_handler_not_installed_when_env_unset
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1466 extracted frob's SIGUSR1 stack-dump handler out of tests/conftest.py
into frob.testing._stackdump (install_stackdump_handler, opt-in via
FROB_COVERAGE_STACKDUMP), closing the WIRE001 unreachable-outside-tests
finding and making the mechanism independently callable by any process.

This ticket is the actual WIRING follow-up T-1466's own body asked for:
call install_stackdump_handler() from frob serve's daemon startup
(src/frob/serve/_daemon.py or wherever the daemon process entry point
lives) and/or frob check's own subprocess pool workers, so a wedge in
either -- not just a pytest worker -- self-diagnoses the same way. Needs
src/frob/serve/** and/or src/frob/check/**, out of T-1466's own declared
scope (tests/conftest.py, src/frob/testing/**).