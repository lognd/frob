---
id: T-5344
title: FMT001 directive-wrap Tier-A pass rewrites directive-shaped lines inside string
  literals (lexical scan, not token-based)
state: queued
kind: bug
origin: human
created: '2026-09-22'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fmt_directives.py
- tests/test_gates_fmt_directives.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Observed on T-5108's first land (2026-09-22): the pre-land FMT001 directive-wrap pass reflowed '# frob:...' continuation lines that lived INSIDE a triple-quoted test fixture string in tests/test_narrative_migrate.py, corrupting the fixture and failing two evidence tests. The wrap must decide from parsed tokens (a comment token, not a physical line starting with '#'), per the owner rule that checks and fixes are token/grammar-based, never lexical. Positive control: a test file whose string literal contains a long '# frob:tests ...' line must be left byte-for-byte untouched by the wrap, while a real comment line of the same text is wrapped.