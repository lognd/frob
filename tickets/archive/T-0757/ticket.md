---
id: T-0757
title: 'design-invariant encoding: import-forbidding frob:invariant + establish-property
  obligation (T-0611/T-0682 class as gates)'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: T-0330
tier: ticket
sprint: null
scope:
- src/frob/graph/dsl.py
- src/frob/gates/**
- src/frob/arch/_normalized.py
- src/frob/tickets/_land.py
- docs/modules/gates.md
- tests/unit/graph/test_dsl.py
- tests/unit/graph/test_dsl_invariant_property.py
- tests/unit/test_design_invariants.py
- invariants/**
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: 'Ticket scope omitted test files, but T-0757''s own mandate requires

    property tests over the real DSL parser (Hypothesis precedent) proving

    existing directives still parse identically before/after the grammar

    change, plus new gate-coverage tests for INV007/INV008 and evidence for

    the two seeded invariants (INV-042/INV-043) -- none of that is

    expressible without touching the test tree. Adding the narrowest test

    globs actually needed rather than a broad tests/** glob.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/graph/test_dsl_invariant_property.py
  reason: 'Ticket scope omitted test files, but T-0757''s own mandate requires

    property tests over the real DSL parser (Hypothesis precedent) proving

    existing directives still parse identically before/after the grammar

    change, plus new gate-coverage tests for INV007/INV008 and evidence for

    the two seeded invariants (INV-042/INV-043) -- none of that is

    expressible without touching the test tree. Adding the narrowest test

    globs actually needed rather than a broad tests/** glob.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/test_design_invariants.py
  reason: 'Ticket scope omitted test files, but T-0757''s own mandate requires

    property tests over the real DSL parser (Hypothesis precedent) proving

    existing directives still parse identically before/after the grammar

    change, plus new gate-coverage tests for INV007/INV008 and evidence for

    the two seeded invariants (INV-042/INV-043) -- none of that is

    expressible without touching the test tree. Adding the narrowest test

    globs actually needed rather than a broad tests/** glob.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: invariants/**
  reason: 'Ticket scope omitted test files, but T-0757''s own mandate requires

    property tests over the real DSL parser (Hypothesis precedent) proving

    existing directives still parse identically before/after the grammar

    change, plus new gate-coverage tests for INV007/INV008 and evidence for

    the two seeded invariants (INV-042/INV-043) -- none of that is

    expressible without touching the test tree. Adding the narrowest test

    globs actually needed rather than a broad tests/** glob.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'Ticket scope omitted test files, but T-0757''s own mandate requires

    property tests over the real DSL parser (Hypothesis precedent) proving

    existing directives still parse identically before/after the grammar

    change, plus new gate-coverage tests for INV007/INV008 and evidence for

    the two seeded invariants (INV-042/INV-043) -- none of that is

    expressible without touching the test tree. Adding the narrowest test

    globs actually needed rather than a broad tests/** glob.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/graph/test_dsl_invariant_property.py::TestBareInvariantUnaffected::test_bare_invariant_parses_with_no_attrs
- tests/unit/graph/test_dsl_invariant_property.py::TestNoImportAttr::test_valid_dotted_path_list_always_parses
- tests/unit/graph/test_dsl_invariant_property.py::TestNoImportAttr::test_empty_no_import_is_malformed
- tests/unit/graph/test_dsl_invariant_property.py::TestNoImportAttr::test_non_dotted_no_import_is_malformed
- tests/unit/graph/test_dsl_invariant_property.py::TestEstablishesAttr::test_non_empty_text_always_parses
- tests/unit/graph/test_dsl_invariant_property.py::TestEstablishesAttr::test_blank_establishes_is_malformed
- tests/unit/test_design_invariants.py::TestInv007::test_forbidden_import_fires
- tests/unit/test_design_invariants.py::TestInv007::test_clean_module_no_finding
- tests/unit/test_design_invariants.py::TestInv007::test_submodule_import_also_forbidden
- tests/unit/test_design_invariants.py::TestInv007::test_lookalike_module_name_not_a_false_positive
- tests/unit/test_design_invariants.py::TestInv007::test_no_obligation_attr_is_unaffected
- tests/unit/test_design_invariants.py::TestInv008::test_missing_property_test_fires
- tests/unit/test_design_invariants.py::TestInv008::test_bound_property_test_clears
- tests/unit/test_design_invariants.py::TestInv008::test_non_property_kind_test_does_not_clear
- tests/unit/test_design_invariants.py::TestInv008::test_no_obligation_attr_is_unaffected
- tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty::test_terminal_side_always_wins_over_non_terminal
- tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty::test_strictly_higher_rank_poorer_side_always_wins
- tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty::test_richer_side_wins_at_equal_or_lower_rank
designated_repro_test: null
acceptance:
- text: GIVEN _normalized.py gains a tree_sitter import WHEN the INV gate runs THEN
    an error fires; GIVEN a comparator invariant declared with a property test THEN
    a violating change fails it; both known cases seeded
  evidence:
  - tests/unit/test_design_invariants.py::TestInv007::test_forbidden_import_fires
  - tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty::test_strictly_higher_rank_poorer_side_always_wins
threat: null
component: null
---
Root-cause analysis 2026-07-22: two rejects (T-0611 tree_sitter imported into the deliberately-pure _normalized.py; T-0682 the newer state must win the splice) were violations of a DESIGN INVARIANT that existed only in the implementers/reviewers head, not as a checkable property. frob already has frob:invariant anchors + INV gates. The thread: module-level design properties (this module must not import X; this comparator must be monotonic in Y; this data model must round-trip) are not being written as invariants at the point they are established, so their violation needs a human skeptic to reconstruct. Deliver: (1) a frob:invariant flavor for IMPORT/DEPENDENCY properties (module M must never import package P) checkable statically -- T-0611s exact case becomes an INV gate error, not a review catch; (2) guidance + lint (docs + a check) that a ticket ESTABLISHING a design property (a new pure module, a new ordering/comparator, a new serialization round-trip) record it as a frob:invariant in the same change; (3) seed the two known ones now: _normalized.py-no-tree_sitter and splice_ledger-newer-wins.