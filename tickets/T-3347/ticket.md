---
id: T-3347
title: 'Fix gate:COV errors: strata-core graph doc anchors, COV003 evidence kind,
  COV007 private-anchor placement'
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
- strata-core/src/graph/model.rs
- strata-core/src/graph/query.rs
- .claude/hooks/frob-suggest.py
- scripts/verify_release_ci_status.py
- src/frob/tickets/_done_report.py
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
Sub-ticket of T-3343 (triage). Fixes the full gate:COV cluster (38 errors -> 0), measured via frob check --only coverage --json:
- COV001 (33): strata-core/src/graph/model.rs and query.rs had zero frob:doc anchors on their public API despite docs/strata/graph.md already documenting every symbol in prose -- added frob:doc directives to model.rs (#model-strata-coresrcgraphmodelrs, GraphError -> #construction-time-refusals-grapherror) and query.rs (#queries-strata-coresrcgraphqueryrs).
- COV003 (2): T-3181/T-3223 (both closed) cited cmd: evidence while kind=bug, which COV003 only allows for kind in [docs, ux]. T-3223: replaced the cmd: evidence node id with the actual pytest node id it ran (frob ticket evidence --replace). T-3181: retriaged kind bug->docs (a repo-hygiene/gitignore fix, no app-behavior code) via frob ticket kind.
- COV007 (3): frob:doc directives were sitting on PRIVATE symbols. frob-suggest.py::_escalate and verify_release_ci_status.py::_run_gh both had a public caller (main/determine_ci_status) already carrying the identical anchor -- removed the redundant private-symbol copy. _done_report.py::_stale_claims_reason has no natural single public caller (called only from a private internal guard step) -- added frob:waive COV007 with reason instead.