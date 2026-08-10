---
id: T-1877
title: Wire T-1824's per-symbol deflation heuristic into a real gate Violation (TEST019)
state: done
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
- src/frob/gates/_coverage.py
- src/frob/gates/_models.py
- tests/test_gates_test019.py
- docs/design/registry/check-coverage.yaml
- tickets/T-1898/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_coverage.py
  reason: Implementing TEST019 requires a new CoverageData field (populated in _coverage.py,
    defined in _models.py) to carry the per-symbol deflation suspects computed by
    _suspect_deflated_symbols through to the gate function in gates/__init__.py, per
    this ticket's own body text anticipating exactly this need.
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/gates/_models.py
  reason: Implementing TEST019 requires a new CoverageData field (populated in _coverage.py,
    defined in _models.py) to carry the per-symbol deflation suspects computed by
    _suspect_deflated_symbols through to the gate function in gates/__init__.py, per
    this ticket's own body text anticipating exactly this need.
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_gates_test019.py
  reason: T-1887 holds a live lease on tests/test_gates.py; adding a dedicated new
    test file instead to avoid the collision while still providing fire/no-fire coverage
    for TEST019.
  actor: logan
  at: '2026-08-09'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: T-1888's lease on check-coverage.yaml is now clear; add the real CHK-GATE-TEST019
    entry here and resolve the now-redundant draft T-1898 (touched by its
    drop commit)
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tickets/T-1898/ticket.md
  reason: T-1888's lease on check-coverage.yaml is now clear; add the real CHK-GATE-TEST019
    entry here and resolve the now-redundant draft T-1898 (touched by its
    drop commit)
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_gates_test019.py::TestTest019DeflatedSymbols::test_flags_suspect_symbol
- tests/test_gates_test019.py::TestTest019DeflatedSymbols::test_clean_when_no_suspects
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1824 added frob.gates._coverage._suspect_deflated_symbols (the per-symbol deflation heuristic: def line hit, every body line 0, corroborated by a frob:tests edge) and wired it into load_coverage as a WARNING log line only -- T-1824's own declared scope (src/frob/gates/_coverage.py, tests/test_gates.py) could not reach frob.gates.__init__.py (where every other Violation-emitting gate function and CoverageData consumer lives), frob.gates._waive.py (_KNOWN_GATE_RULES must register a new rule id, e.g. TEST019, before any gate can emit it without a WIRE001 finding), or docs/modules/gates.md (the frob:enumerates anchor for _KNOWN_GATE_RULES, plus a docs section describing the new rule -- leased by another epic at T-1824's land time). This ticket is that follow-up: add a _test019_deflated_symbols-shaped violation-emitting function in gates/__init__.py consuming CoverageData (which will likely need a new field carrying the suspect symref list, computed by _suspect_deflated_symbols during load_coverage), register TEST019 in _KNOWN_GATE_RULES, and document it in gates.md alongside TEST011/TEST017.