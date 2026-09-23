---
id: T-5270
title: frob:tests parse fails on a quoted target immediately followed by a trailing
  noqa suffix
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-4712: a directive whose target is QUOTED (frob:tests "some title") and is immediately followed on the same physical line by a bare '# noqa: E501' comment (no other attrs) fails to parse -- MalformedDirective 'bad attribute syntax: ...'. Root cause: _QUOTED_TARGET_RE's trailing \s* already consumes the whitespace between the closing quote and the '#', so _parse_attrs' tail-comment regex (?<=\s)# never matches (it requires a preceding space still present in attr_text) and the noqa text is misread as an unparseable attribute instead of being recognized and stripped as a trailing suppression marker. T-4712's quoted-target wrap narrowing (never cutting inside a quoted target) newly produces this exact shape (an otherwise-unsplittable quoted target getting the unsplittable-remainder noqa suffix appended directly after it) where previously the naive word-boundary wrapper always found SOME cut point inside the quote first.