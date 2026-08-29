---
id: T-3347
title: 'Fix gate:COV errors: strata-core graph doc anchors, COV003 evidence kind,
  COV007 private-anchor placement'
state: done
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
- docs/strata/graph.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/strata/graph.md
  reason: COV001 fix touches this doc file's inbound-edge count only, not its content
  actor: logan
  at: '2026-08-29'
body_changes:
- mode: append
  reason: 'BUG002: no genuine before/after repro exists for a doc-comment-only diff;
    declaring no-behavior-change per BUG002 remedy (2) rather than inventing an artificial
    behavior test'
  actor: logan
  at: '2026-08-29'
  old_length: 1279
  new_length: 1938
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov001_passes_when_documented
- tests/test_gates.py::TestCoverageGate::test_cov003_passes_when_evidence_collected
- tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_declared_entrypoint_is_exempt
- tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_same_file_undeclared_still_fires
- tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_library_module_still_fires_when_another_file_is_declared
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: dd155ff20bd3cfbc8d1e41828ed78e74437ab64d
---
Sub-ticket of T-3343 (triage). Fixes the full gate:COV cluster (38 errors -> 0), measured via frob check --only coverage --json:
- COV001 (33): strata-core/src/graph/model.rs and query.rs had zero frob:doc anchors on their public API despite docs/strata/graph.md already documenting every symbol in prose -- added frob:doc directives to model.rs (#model-strata-coresrcgraphmodelrs, GraphError -> #construction-time-refusals-grapherror) and query.rs (#queries-strata-coresrcgraphqueryrs).
- COV003 (2): T-3181/T-3223 (both closed) cited cmd: evidence while kind=bug, which COV003 only allows for kind in [docs, ux]. T-3223: replaced the cmd: evidence node id with the actual pytest node id it ran (frob ticket evidence --replace). T-3181: retriaged kind bug->docs (a repo-hygiene/gitignore fix, no app-behavior code) via frob ticket kind.
- COV007 (3): frob:doc directives were sitting on PRIVATE symbols. frob-suggest.py::_escalate and verify_release_ci_status.py::_run_gh both had a public caller (main/determine_ci_status) already carrying the identical anchor -- removed the redundant private-symbol copy. _done_report.py::_stale_claims_reason has no natural single public caller (called only from a private internal guard step) -- added frob:waive COV007 with reason instead.

frob:no-behavior-change reason="comment/annotation-only fix: adds frob:doc directives to strata-core/src/graph/{model,query}.rs (zero runtime code changed, rust module unmodified functionally), removes a redundant frob:doc line from two Python private helpers whose public caller already carries the identical anchor, and adds one frob:waive COV007 comment -- no application behavior, CLI output, or test-observable code path changed anywhere in this diff. The COV003 evidence-kind fixes for T-3181/T-3223 (kind retriage, evidence rebind to the real pytest node id already run) are separate already-landed ledger-only ticket commits, not part of this diff."