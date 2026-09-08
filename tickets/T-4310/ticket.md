---
id: T-4310
title: SCOPE002 is unwaivable since the ledger migrated off single-file tickets.md
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- src/frob/gates/__init__.py
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
Discovered while working T-4301 (frob release status CLI wiring). SCOPE002 (scope-closure doc/test/private-helper nudge) is promoted to error severity in frob.toml, but its Violation is always emitted with file='tickets.md' (src/frob/gates/__init__.py::_scope002_violation). No real tickets.md exists any more in this repo's per-ticket-directory ledger format (tickets/T-####/ticket.md), and the graph walker never parses those per-ticket files for directives (frob.graph.__init__'s is_ledger check only recognizes a repo-ROOT tickets.md). Confirmed via load_or_build_snapshot(...).edges: zero WAIVE edges anywhere in the repo target SCOPE002, even though several closed tickets (T-4298, T-1010, T-4286, T-4013) carry a documented frob:waive SCOPE002 reason= block in their ticket.md body -- those directives are dead text, never parsed into a real WAIVE edge, so frob.gates._waive._match_waiver can never match a SCOPE002 violation (it requires waiver.src == tickets.md or waiver_file == tickets.md, and SCOPE002 is not in _PACKAGE_SCOPED_RULES either). Practical effect: any ticket whose scope includes a file with a pre-existing frob:tests/frob:doc edge into a large shared file (e.g. tests/test_release.py, which covers most of src/frob/release/star star) is forced to either widen scope to the entire transitive doc/test closure (which can cascade into unrelated shared modules like src/frob/gates/__init__.py and docs/modules/gates.md/perf.md) or carry a permanently-broken gate:SCOPE failure with no way to record acceptance. Fix options: 1) make _scope002_violation's file/symref carry the owning ticket's real ticket.md path so a directive placed there actually parses, or 2) add SCOPE002 to a ticket-level ack path (scope_breadth_ack already exists for TICK009; extend gate:SCOPE to honor it for SCOPE002), or 3) demote SCOPE002 back to warn in frob.toml until 1/2 ships. T-4301 worked around this by widening scope to the release module siblings and accepting the residual SCOPE002 findings against gates/__init__.py's own closure as a measured, unwaivable gap -- see T-4301's Done report.