---
id: T-0167
title: 'frob sys --help: add example invocations and directory-root convention'
state: done
kind: docs
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/__main__.py
- docs/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
Typani pilot: sys subcommand help gives no example invocation or the design-root directory convention -- the pilot reverse-engineered usage from frob.strata comments. Add epilog examples (plan/doc/audit/export against a design root) to the argparse help and a quickstart paragraph in docs.