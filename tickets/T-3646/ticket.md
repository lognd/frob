---
id: T-3646
title: 'refactor split: archived-ticket evidence citation rewriter mis-attributes
  symbol to wrong destination across sequential split calls'
state: queued
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/**
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
Found while working T-3593 (split tests/test_vet.py, reusing T-3586/T-3596's recipe), sibling gap to the import-consolidation one filed alongside this.

When a source module's classes are split into SEVERAL different destination modules across sequential frob refactor split invocations (e.g. TestCapabilityScan -> test_capability_scan_python.py, then TestCapabilityScanTsBindingResolution -> test_capability_scan_ts.py, TestCapabilityScanRustBindingResolution -> test_capability_scan_rust.py, etc., all splitting out of the same tests.test_vet source module), the archived-ticket evidence citation rewriter mis-attributed EVERY non-python capability-scan class's evidence citations in archived tickets to test_capability_scan_python.py (the destination of the FIRST split call touching a TestCapabilityScan*-prefixed symbol) instead of that specific class's own real destination.

Repro (T-3593): after splitting TestCapabilityScan into tests.vet_suite.test_capability_scan_python, then later splitting TestCapabilityScanTsBindingResolution into tests.vet_suite.test_capability_scan_ts (a separate destination module), grep the archived tickets:
  git grep 'test_capability_scan_python.py::TestCapabilityScanTs' -- tickets/archive/
-> 12 archived tickets (T-0377, T-0378, T-0379, T-0432, T-0660, T-0661, T-0662, T-0663, T-0664, T-0666, T-1063, T-1500) had their evidence citations for Ts/Rust/C/Cpp/Kotlin capability-scan test classes all rewritten to point at test_capability_scan_python.py, where those classes do not exist. Landing the split ticket as-is triggers OrphanedEvidenceDeletion on every one of those 12 tickets (frob ticket land's own guard caught it; the split verb's own post-condition checks did not).

Suggested fix: the archived-ticket citation rewrite should re-derive each citation's NEW destination from that specific symbol's own move record for THIS invocation, not from a cached 'last known destination for any symbol whose name starts with the prefix I am currently splitting' state that leaks across sequential split calls in the same session.