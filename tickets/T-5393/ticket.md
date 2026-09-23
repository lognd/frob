---
id: T-5393
title: 'ruff ''Would reformat: path'' colon form breaks _land_format and check/_python
  parsers (bogus filenames)'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_land_format.py
- src/frob/check/_python.py
- docs/modules/gates.md
- tests/unit/test_land_format_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_land_format.py
  reason: fix colon-form ruff Would reformat parser
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/check/_python.py
  reason: fix colon-form ruff Would reformat parser
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/modules/gates.md
  reason: update LANDFMT001 notes for shared parser
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/test_land_format_gate.py
  reason: regression test for land-format rewrite path receiving real paths
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Newer ruff prints 'Would reformat: <path>' (colon). src/frob/gates/_land_format.py:143 and src/frob/check/_python.py:223 both strip only 'Would reformat ' so the residual string 'Would reformat: <path>' is used as a filename. Observed in /tmp/land-T-5302.log: hundreds of 'error: Failed to format Would reformat: tests/...: No such file or directory' during the pre-land rewrite, after which the land falls back to LANDFMT001 refusal on unrewritten drift; in frob check the Diagnostic.file is wrong so waiver/scope matching is voided (path-shape identity). Fix: one shared parser (extract, no duplicate) that accepts both forms via a regex anchored on the ruff line grammar, positive-control test with both output shapes, and a regression test that the rewrite receives real paths.