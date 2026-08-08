---
id: T-1885
title: verify_import_resolution ast.parses every touched file with no Python-extension
  filter
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/refactor/_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Found while writing T-1854's regression tests.
`verify_import_resolution` (src/frob/refactor/_verify.py) calls
`ast.parse` on every path in `touched_files` unconditionally -- no
filter for a `.py` extension. Any `RefactorPlan.reference_ops` entry
touching a non-Python file (a `tickets/<id>/ticket.md`, a
`docs/design/registry/*.yaml`, any prose/doc carrier) makes
`run_refactor`'s Verify phase try to parse that file as Python, fail
(observed: "leading zeros in decimal integer literals are not
permitted" parsing a ticket.md's `T-0001`-shaped id), and roll the
whole transaction back -- even though nothing about the actual rewrite
was wrong.

This means `frob refactor rename`'s existing ticket-evidence carrier
(T-1546, `scan_evidence_citations`) and registry carrier (T-1200,
`scan_registry_citations`) are BOTH silently non-functional through the
real `run_refactor` end-to-end path today whenever they produce a hit
-- confirmed by reproduction, not assumed: a ticket carrying a real
evidence citation for a moving symbol causes `run_refactor` to roll
back. `scan_evidence_citations`/`build_plan` themselves are unaffected
(no verify step runs there), so this was invisible to every existing
scan-level unit test, which is presumably why it was never caught.

Fix: filter `touched_files` to a `.py` suffix before the parse loop, or
skip a file whose suffix cannot possibly be Python source, in
`verify_import_resolution`. Add a regression test that runs a plan
touching a non-Python file (a ticket.md carrier is the simplest real
repro) through `run_refactor` and asserts it does NOT roll back for
this reason.
