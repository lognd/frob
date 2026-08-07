---
id: T-1785
title: 'test_ticket_runner_archive_force.py::test_force_overrides_the_live_lease_refusal
  fails: T-1762 reason requirement not accounted for'
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_ticket_runner_archive_force.py
- src/frob/app/ticket_runner/_archive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Pre-existing failure, unrelated to T-1750 (confirmed via git diff main -- both files: zero diff from main). T-1762 added a --reason/--reason-file requirement to frob ticket archive --force whenever a live lease exists; test_force_overrides_the_live_lease_refusal predates T-1762 and calls ticket_run with force=True and no reason, so it now hits sys.exit(1) instead of completing. Found while working T-1750; out of that ticket's declared scope.