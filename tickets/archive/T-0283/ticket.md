---
id: T-0283
title: 'perf: drive 4 remaining PERF findings to zero (fix or reasoned waive)'
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_obfuscation.py
- src/frob/tickets/_land.py
- src/frob/strata/_host_isolation.py
- src/frob/deploy/_generate.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/deploy/test_generate.py::TestSorted::test_sorted
designated_repro_test: null
threat: null
component: null
---
