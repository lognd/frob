---
id: T-3573
title: 'frob-arch god-module/god-class remainder: 14 module-split + 1 class-split
  design campaigns'
state: queued
kind: bug
origin: agent
created: '2026-08-31'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_coverage.py
- src/frob/gates/_waive.py
- src/frob/gitio.py
- src/frob/graph/__init__.py
- src/frob/graph/callgraph.py
- src/frob/lang/__init__.py
- src/frob/lang/_common.py
- src/frob/lang/_support.py
- src/frob/perf/_sketch_store.py
- src/frob/render/_elements.py
- src/frob/stats/_sketch.py
- src/frob/strata/_sysdoc.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_evidence.py
- src/frob/tickets/_models.py
- src/frob/tickets/_reporting.py
- src/frob/tickets/_store.py
- src/frob/render/_renderer.py
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
Filed while triaging T-3494 (frob-arch WARN remainder after T-2379). 14 god-module findings (10-75 exports each) plus 1 god-class finding, none fixed by T-2379/T-3494 -- each is a genuine module/class-split design exercise (splitting a big module along its own naming/usage clusters, or extracting a mixin/helper class), real design judgment, not mechanical, and each is its own small campaign per T-2379's own body. Do not blanket-split to hit zero; triage per-file, splitting only where a real usage-cluster seam exists.

god-module (14): src/frob/gates/_coverage.py, src/frob/gates/_waive.py, src/frob/gitio.py, src/frob/graph/__init__.py, src/frob/graph/callgraph.py, src/frob/lang/__init__.py, src/frob/lang/_common.py, src/frob/lang/_support.py, src/frob/perf/_sketch_store.py, src/frob/render/_elements.py, src/frob/stats/_sketch.py, src/frob/strata/_sysdoc.py, src/frob/tickets/__init__.py, src/frob/tickets/_evidence.py, src/frob/tickets/_models.py, src/frob/tickets/_reporting.py, src/frob/tickets/_store.py

god-class (1): src/frob/render/_renderer.py::RenderWriter (16 methods vs threshold 12)

Re-measure via: uv run frob check --only arch --json (unscoped), filter category in (god-module, god-class). Split into per-file/per-cluster children as work actually begins on each -- this rollup exists so the remainder is tracked as real tickets instead of only prose in T-3494's own closed body.
