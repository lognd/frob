---
id: T-3225
title: 'WAIVE006: AFFECT001 waiver on _rule_id_scan.py bound to closed ticket T-2993'
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
- src/frob/gates/_rule_id_scan.py
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

tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo
fails on main (measured post-T-3029, T-3041 investigation):

  WAIVE006: src/frob/gates/_rule_id_scan.py::scan_emitted_rule_ids waives
  frob:waive AFFECT001, bound to ticket T-2993, which is DONE/DROPPED; a
  waiver justified by a pending ticket must not outlive it -- re-justify
  with a current reason (and, if still needed, an open follow-on ticket)
  or remove the waiver now that the gap it excused has presumably been
  addressed.

Fix: read the frob:waive AFFECT001 comment above scan_emitted_rule_ids,
determine whether the AFFECT001 gap it excused is still real, and either
remove the waiver (if the doc drift it excused has since been fixed) or
re-justify it against a currently-open ticket.