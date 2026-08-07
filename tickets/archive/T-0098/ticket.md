---
id: T-0098
title: frob ticket attach without path should error usefully outside a TTY
state: done
kind: bug
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- tests/**
- docs/modules/tickets.md
- tickets.md
- src/frob/__main__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_ticket.py::TestTicketAttachNonInteractive::test_attach_without_path_fails_fast_off_tty
designated_repro_test: null
threat: null
component: null
---
Malmberg adoption agent gap report: frob ticket attach with no path argument attempts clipboard-image capture even in a non-interactive agent session, instead of failing fast with a clear message (or accepting a text note). Agents cannot paste from a clipboard; the command should detect no-TTY and error with remedy text.