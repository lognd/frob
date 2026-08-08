---
id: T-1823
title: wire frob serve daemon / check subprocess pool into the SIGUSR1 stack-dump
  handler
state: queued
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/serve/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
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
