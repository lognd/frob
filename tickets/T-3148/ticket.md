---
id: T-3148
title: _KNOWN_RULE_FIXABILITY literal missing SYS100 (T-3140 item 4)
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/
  reason: 'narrowed: only the checked-in _KNOWN_RULE_FIXABILITY literal needs the
    SYS100 entry added'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/gates/_wire.py
  reason: 'narrowed: only the checked-in _KNOWN_RULE_FIXABILITY literal needs the
    SYS100 entry added'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_gates.py
  reason: 'narrowed: only the checked-in _KNOWN_RULE_FIXABILITY literal needs the
    SYS100 entry added'
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description
tests/test_gates.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan
fails: the checked-in `_KNOWN_RULE_FIXABILITY` literal (production file
under src/frob/gates/, out of T-3140's declared scope) is missing
`{'SYS100': 'auto'}` that a fresh scan now reports. A new rule SYS100 was
added with auto-fixability and the checked-in literal was never
regenerated against it.

## Plan
Locate `_KNOWN_RULE_FIXABILITY` (src/frob/gates/), regenerate/add the
SYS100 entry, and re-run the test to confirm it passes.
