---
id: T-3031
title: TestCheckTypescript::test_clean_ts_passes_tsc fails on main (REF001 on node_modules/package.json/tsconfig.json,
  MILE003 on real tickets.md)
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_check.py
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
Found while root-causing T-3019 (spurious REF001/PRE001/SCOPE001 on a
clean project) -- not in T-3019's own confirmed repro list, and a
different fixture shape (a real TypeScript project reusing this repo's
shared FIXTURES helper), so split out rather than folded in.

tests/system/test_cli_check.py::TestCheckTypescript::test_clean_ts_passes_tsc
fails on unmodified main with 6 gate errors: REF001 on node_modules,
package.json, src.ts, tickets.md, tsconfig.json, plus MILE003 on a real
ticket id (T-0329) apparently pulled from this repo's own tickets.md
content rather than a synthetic fixture ledger. Needs investigation into
why this fixture's tickets.md carries live repo ticket ids at all, plus
the same REF001-orphan class T-3019 fixed for the Python clean-project
fixture, applied to (or exempted for) this TS fixture's own manifest
files.
