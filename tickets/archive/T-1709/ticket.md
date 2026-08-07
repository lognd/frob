---
id: T-1709
title: Fix INV006/PII012 findings introduced by T-1700's _markdown_scan.py
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_markdown_scan.py
- tests/unit/gates/test_markdown_scan.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_line_wrapped_inline_span_is_blanked_as_one_token
designated_repro_test: null
threat: null
component: null
---
T-1700's land introduced two new unscoped gate findings, caught by
`frob check --land-parity` immediately after landing:

- INV006: src/frob/gates/_markdown_scan.py's module docstring uses
  exclusivity language ("only") with no bound invariant -- needs the
  same `frob:waive INV006 preset="split-carried-prose"` treatment this
  repo's other design-rationale-heavy modules already carry.
- PII012: tests/unit/gates/test_markdown_scan.py:62's test function name
  `test_line_wrapped_inline_span_is_blanked_as_one_token` matches the
  PII-shaped keyword heuristic (category credentials, on the substring
  "token") -- a plain false positive, needs `frob:waive PII012
  reason="..."`.

Both are cosmetic/waiver fixes, no behavior change.