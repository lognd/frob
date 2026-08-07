---
id: T-0010
title: 'frob serve: MCP adapter over stale_docs/doable_tickets/check_scope/pre_work'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- tests/test_serve.py
- docs/modules/serve.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_serve.py::TestBuildServer::test_registers_all_five_tools
designated_repro_test: null
threat: null
component: null
---
MCP adapter exposing stale_docs/doable_tickets/check_scope/pre_work queries as MCP tools, so agent clients can query frob state without shelling out. Deferred post-0.1.0.