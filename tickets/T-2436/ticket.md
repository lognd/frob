---
id: T-2436
title: 'T-2390 child: validate [test] table against a declared schema'
state: in-progress
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: T-2390
tier: story
sprint: null
runs_last: false
scope:
- tests/unit/test_test_table_schema.py
- src/frob/gates/__init__.py
- src/frob/check/__init__.py
- frob.toml
- docs/modules/gates.md
- docs/design/registry/check-coverage.yaml
- .frob-release.json
- CHANGELOG.md
- pyproject.toml
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/check/_native.py
  reason: actual reader is frob.testing._runners (not check._native/gates.__init__
    as originally guessed); gate registration + release wiring, same pattern as prior
    T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/__init__.py
  reason: actual reader is frob.testing._runners (not check._native/gates.__init__
    as originally guessed); gate registration + release wiring, same pattern as prior
    T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/check/__init__.py
  reason: actual reader is frob.testing._runners (not check._native/gates.__init__
    as originally guessed); gate registration + release wiring, same pattern as prior
    T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: frob.toml
  reason: actual reader is frob.testing._runners (not check._native/gates.__init__
    as originally guessed); gate registration + release wiring, same pattern as prior
    T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/gates.md
  reason: actual reader is frob.testing._runners (not check._native/gates.__init__
    as originally guessed); gate registration + release wiring, same pattern as prior
    T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: actual reader is frob.testing._runners (not check._native/gates.__init__
    as originally guessed); gate registration + release wiring, same pattern as prior
    T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: .frob-release.json
  reason: actual reader is frob.testing._runners (not check._native/gates.__init__
    as originally guessed); gate registration + release wiring, same pattern as prior
    T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: CHANGELOG.md
  reason: actual reader is frob.testing._runners (not check._native/gates.__init__
    as originally guessed); gate registration + release wiring, same pattern as prior
    T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: pyproject.toml
  reason: actual reader is frob.testing._runners (not check._native/gates.__init__
    as originally guessed); gate registration + release wiring, same pattern as prior
    T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: uv.lock
  reason: actual reader is frob.testing._runners (not check._native/gates.__init__
    as originally guessed); gate registration + release wiring, same pattern as prior
    T-2390 children
  actor: logan
  at: '2026-08-18'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Validate the `[test]` table (16 leaves) against a declared schema.
Readers are spread across frob.check._native and frob.gates.__init__ --
NOT fully inventoried at T-2390 filing time; do that as this child's own
first step.

Same required shape as every T-2390 child: module:symbol declared
schema (T-2397's resolve_dotted_symbol precedent), must-now-fire +
must-still-pass fixtures, Severity.UNRESOLVED (never silent) when no
schema is declared, portable (no hardcoded frob-specific reference).

Part of T-2390's epic decomposition -- see T-2390's body for the full
disjoint-readers finding and sibling children.
