---
id: T-0030
title: ticket new --origin flag
state: done
kind: ux
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/app/**
- src/frob/__main__.py
evidence:
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_plan_then_sweep_flow
attachments: []
---

## Done report

frob ticket new --origin {human,agent,auditor}; agents can now file
tickets with correct provenance instead of hand-editing frontmatter.
