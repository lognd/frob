---
id: T-3405
title: OPAQUE001 _SUBSCRIPT_CALL_RE crosses statement boundaries (regex, not AST)
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_scan.py
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
OPAQUE001's container-dynamic-key-call detector (_SUBSCRIPT_CALL_RE, python:runtime:container-dynamic-key-call) is a byte regex over raw source, not an AST/statement-bound scan. Its trailing \s*\( allows the whitespace class to match a newline, so a plain subscript read on one line followed by an unrelated statement that happens to start with '(' on the next line is misread as 'container[key](...)' -- found at tests/unit/test_land_finish_idempotent.py:243 (T-3392, waived there with a full explanation). Standing directive: checks must compare SYMBOLS via the parser, not lexical text -- this is exactly that class of defect (LEXCHECK001's own family), but LEXCHECK001 itself only scans DETECTOR_PACKAGE_ROOTS (src/frob/gates/**), not src/frob/vet/**, so it did not catch this one. Fix: bind the match to a single statement/expression (AST-based, or at minimum require the closing paren's following char sequence to stay within one logical line/statement) so a coincidental cross-statement bracket-then-paren sequence cannot false-fire. Filed from T-3392's Done report.