---
id: T-3223
title: 'DOC006: dead path pointers in tickets/T-2962/ticket.md'
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-2962/ticket.md
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
Split from T-3041's triage (13 live-repo self-conformance tests fail).

tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo
fails on main (measured post-T-3029, T-3041 investigation) with two
DOC006 findings, both in tickets/T-2962/ticket.md:

  line 50: 'src/frob/gates/_platform_guards.py' is not a tracked file
  line 54: 'tests/test_platform_guards_gate.py' is not a tracked file

Fix: either those paths were renamed/removed since T-2962 was written
(update the ticket's own pointers to the real current paths) or the
files never landed as named (add a frob:waive DOC006 directive with a
reason on each line if the reference is intentionally illustrative or
future-facing).
