---
id: T-1746
title: Implement real fix for WIRE001 same-file test-fixture reuse false positive
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_tickets_mutation_evidence.py
- src/frob/gates/_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
`tests/test_tickets_mutation_evidence.py::_repo_with_add_change` carries
a `frob:waive WIRE001` (T-1727's own land) because WIRE001's same-file
exclusion rule (T-1592/T-1558's precedent: a test-tree symbol's OWN
defining file never counts as a "reached" caller, only a DIFFERENT test
file does) does not recognize a shared fixture helper reused by two
test classes within one file as wired, even though every call site is a
real `test_*` method, verifiable by reading the file directly.

Two ways to close this honestly:
1. Move `_repo_with_add_change` to a location a genuinely different
   test file could plausibly reuse (a shared fixtures module), so a real
   cross-file caller exists and the waiver can be dropped.
2. If same-file test-fixture reuse is a legitimate, common shape (it
   plausibly is -- DUP001 actively REQUIRES this exact extraction
   whenever two test classes in one file develop near-identical setup
   bodies), extend WIRE001's `_wire_test_path_excluded` same-file rule
   to also recognize a call from ANY `test_*`-prefixed function/method
   in the SAME file as a genuine reach class, not just cross-file reuse.

Either fix removes the T-1727 waiver's need to exist.