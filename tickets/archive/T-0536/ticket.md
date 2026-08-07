---
id: T-0536
title: Retag/rebind 3 residual COV006 findings after T-0528 calibration (genuinely
  wrong bindings, not blindness)
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_graph.py
- tests/unit/strata/test_selfconform.py
- tests/system/test_cli_ticket_land.py
- Makefile
- docs/modules/testing.md
- src/frob/gates/__init__.py
- tests/test_coverage.py
- tests/test_gates_tick005.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: Makefile
  reason: 'SCOPE001 collision: T-0538/T-0537''s own already-closed changes are still
    in this worktree''s uncommitted-vs-main diff (sequential tickets, one worktree);
    not new edits by T-0536 itself'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/testing.md
  reason: 'SCOPE001 collision: T-0538/T-0537''s own already-closed changes are still
    in this worktree''s uncommitted-vs-main diff (sequential tickets, one worktree);
    not new edits by T-0536 itself'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'SCOPE001 collision: T-0538/T-0537''s own already-closed changes are still
    in this worktree''s uncommitted-vs-main diff (sequential tickets, one worktree);
    not new edits by T-0536 itself'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_coverage.py
  reason: 'SCOPE001 collision: T-0538/T-0537''s own already-closed changes are still
    in this worktree''s uncommitted-vs-main diff (sequential tickets, one worktree);
    not new edits by T-0536 itself'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_gates_tick005.py
  reason: 'SCOPE001 collision: T-0538/T-0537''s own already-closed changes are still
    in this worktree''s uncommitted-vs-main diff (sequential tickets, one worktree);
    not new edits by T-0536 itself'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'SCOPE001 collision: T-0538/T-0537''s own already-closed changes are still
    in this worktree''s uncommitted-vs-main diff (sequential tickets, one worktree);
    not new edits by T-0536 itself'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_graph.py::TestBuildIncremental::test_fingerprint_packages_derived_from_lang_registry
- tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock::test_scanned_languages_equals_registry_languages
- tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
designated_repro_test: null
threat: null
component: null
---
T-0528's COV006 calibration pass fixed 54/57 dogfooded findings via checker-side rescues (implicit dunder/validator dispatch, transitive 3+-file import chains, kind=integration/e2e exemption, non-python target exemption). 3 residual findings could not be fixed from src/frob/gates/__init__.py alone -- scope=[docs/modules/gates.md, src/frob/gates/__init__.py] does not cover the test files that need editing:

1. tests/test_graph.py::TestBuildIncremental.test_fingerprint_packages_derived_from_lang_registry -> src/frob/graph/cache.py::_compute_fingerprint -- GENUINELY WRONG BINDING: the test only asserts GRAMMAR_FINGERPRINT_PACKAGES <= set(graph_cache._FINGERPRINT_PACKAGES), never calling _compute_fingerprint at all. Same shape as the T-0516 file-level waiver already on tests/test_gates.py (module-constant drift lock, not a call). Fix: either rebind the frob:tests directive to whatever symbol actually computes/owns _FINGERPRINT_PACKAGES, or add a frob:waive COV006 with the real reason (constant drift-lock, no call to bind against).

2. tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock.test_scanned_languages_equals_registry_languages -> src/frob/strata/_selfconform.py::_sorted_capability_files -- same shape: asserts set membership over module constants, never calls _sorted_capability_files.

3. tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock.test_extended_kinds_is_disjoint_from_kind_map -> src/frob/strata/_selfconform.py::_observed_extended_kinds_by_node -- same shape: asserts _EXTENDED_KINDS.isdisjoint(_KIND_MAP.keys()) and a union equality, never calls _observed_extended_kinds_by_node.

Also noted during T-0528: frob.graph.callgraph's build_call_graph resolves privacy via _short_name(qualname).startswith('_') -- a PYTHON-only naming convention. Rust's fn/pub fn convention has no such marker, so every rust callee looks 'public' to it and is silently never recorded as a private edge (this is what made all 7 frob-core/src/lib.rs COV006 findings structurally invisible before T-0528 added a non-python-target exemption to COV006 itself as a stopgap). A real fix belongs in frob.graph.callgraph (out of COV006's scope): add real per-language privacy resolution (e.g. consult RawSymbol.public directly instead of re-deriving it from the qualname's leading underscore) so Rust/other non-python languages get real call-graph edges instead of being permanently exempted from this class of check.