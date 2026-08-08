---
id: T-1877
title: Wire T-1824's per-symbol deflation heuristic into a real gate Violation (TEST019)
state: queued
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1824 added frob.gates._coverage._suspect_deflated_symbols (the per-symbol deflation heuristic: def line hit, every body line 0, corroborated by a frob:tests edge) and wired it into load_coverage as a WARNING log line only -- T-1824's own declared scope (src/frob/gates/_coverage.py, tests/test_gates.py) could not reach frob.gates.__init__.py (where every other Violation-emitting gate function and CoverageData consumer lives), frob.gates._waive.py (_KNOWN_GATE_RULES must register a new rule id, e.g. TEST019, before any gate can emit it without a WIRE001 finding), or docs/modules/gates.md (the frob:enumerates anchor for _KNOWN_GATE_RULES, plus a docs section describing the new rule -- leased by another epic at T-1824's land time). This ticket is that follow-up: add a _test019_deflated_symbols-shaped violation-emitting function in gates/__init__.py consuming CoverageData (which will likely need a new field carrying the suspect symref list, computed by _suspect_deflated_symbols during load_coverage), register TEST019 in _KNOWN_GATE_RULES, and document it in gates.md alongside TEST011/TEST017.