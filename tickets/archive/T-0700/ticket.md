---
id: T-0700
title: 'strata grammar: access modes + shared-resource/lease declarations for contention
  proofs'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: T-0331
tier: ticket
sprint: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- editors/**
- docs/strata/**
- tests/unit/strata/
- docs/guides/extending/strata-surface-grammar.md
- design/frob.strata
- tests/test_tickets_live_tracker.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/guides/extending/strata-surface-grammar.md
  reason: T-0700 grammar deliverable touches this doc (AFFECT001 closure for parse.rs::Parser.parse_program's
    affects-doc)
  actor: logan
  at: '2026-07-27'
- op: add
  glob: design/frob.strata
  reason: 'close-time live-tracker re-point: 5 SYS203 waivers cite T-0700 by design,
    must repoint to the successor ticket to close'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_tickets_live_tracker.py
  reason: 'close-time live-tracker re-point: fixture line cites T-0700 as a placeholder
    ticket id'
  actor: logan
  at: '2026-07-27'
evidence:
- strata-core/src/parse/mod.rs::tests::parses_node_access_clause
- strata-core/src/parse/mod.rs::tests::parses_store_access_clause
- strata-core/src/parse/mod.rs::tests::parses_all_access_modes
- strata-core/src/parse/mod.rs::tests::error_access_rejects_unknown_mode
- strata-core/src/parse/mod.rs::tests::error_access_requires_mode_keyword
- strata-core/src/parse/mod.rs::tests::parses_resource_with_arbitrated_by
- strata-core/src/parse/mod.rs::tests::parses_resource_with_lock
- strata-core/src/parse/mod.rs::tests::parses_bare_resource_with_no_arbiter
- strata-core/src/parse/mod.rs::tests::error_resource_rejects_both_arbitrated_by_and_lock
- tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_reads_access_attrs
- tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_no_access_attrs_is_empty
- tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_unrecognized_mode_fails_closed
- tests/unit/strata/test_access.py::TestModeConflict::test_read_read_is_safe
- tests/unit/strata/test_access.py::TestModeConflict::test_read_alpha_is_safe
- tests/unit/strata/test_access.py::TestModeConflict::test_alpha_alpha_conflicts
- tests/unit/strata/test_access.py::TestModeConflict::test_write_conflicts_with_anything
- tests/unit/strata/test_access.py::TestModeConflict::test_exclusive_conflicts_with_everything_including_itself
- tests/unit/strata/test_access.py::TestModeConflict::test_append_conflicts_with_anything
- tests/unit/strata/test_access.py::TestResourceContentionViolations::test_two_writers_no_arbiter_fires
- tests/unit/strata/test_access.py::TestResourceContentionViolations::test_arbitrated_by_discharges
- tests/unit/strata/test_access.py::TestResourceContentionViolations::test_lock_discharges
- tests/unit/strata/test_access.py::TestResourceContentionViolations::test_read_only_modes_discharge_without_arbiter
- tests/unit/strata/test_access.py::TestResourceContentionViolations::test_bare_resource_declaration_with_no_arbiter_still_fires
- tests/unit/strata/test_access.py::TestResourceContentionViolations::test_single_accessor_never_fires
- tests/unit/strata/test_access.py::TestResourceContentionViolations::test_unrelated_resources_do_not_cross_conflict
- tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally
- tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
- strata-core/src/parse/mod.rs::tests::parses_node_access_clause
- strata-core/src/parse/mod.rs::tests::parses_store_access_clause
- strata-core/src/parse/mod.rs::tests::parses_all_access_modes
- strata-core/src/parse/mod.rs::tests::error_access_rejects_unknown_mode
- strata-core/src/parse/mod.rs::tests::error_access_requires_mode_keyword
- strata-core/src/parse/mod.rs::tests::parses_resource_with_arbitrated_by
- strata-core/src/parse/mod.rs::tests::parses_resource_with_lock
- strata-core/src/parse/mod.rs::tests::parses_bare_resource_with_no_arbiter
- strata-core/src/parse/mod.rs::tests::error_resource_rejects_both_arbitrated_by_and_lock
designated_repro_test: null
acceptance:
- text: GIVEN two nodes with write-mode access to one resource and no arbiter WHEN
    sys checks run THEN a fail-closed error; GIVEN the same with a declared arbiter
    or read-only modes THEN the obligation discharges
  evidence:
  - strata-core/src/parse/mod.rs::tests::parses_node_access_clause
  - strata-core/src/parse/mod.rs::tests::parses_store_access_clause
  - strata-core/src/parse/mod.rs::tests::parses_all_access_modes
  - strata-core/src/parse/mod.rs::tests::error_access_rejects_unknown_mode
  - strata-core/src/parse/mod.rs::tests::error_access_requires_mode_keyword
  - strata-core/src/parse/mod.rs::tests::parses_resource_with_arbitrated_by
  - strata-core/src/parse/mod.rs::tests::parses_resource_with_lock
  - strata-core/src/parse/mod.rs::tests::parses_bare_resource_with_no_arbiter
  - strata-core/src/parse/mod.rs::tests::error_resource_rejects_both_arbitrated_by_and_lock
  - tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_reads_access_attrs
  - tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_no_access_attrs_is_empty
  - tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_unrecognized_mode_fails_closed
  - tests/unit/strata/test_access.py::TestModeConflict::test_read_read_is_safe
  - tests/unit/strata/test_access.py::TestModeConflict::test_read_alpha_is_safe
  - tests/unit/strata/test_access.py::TestModeConflict::test_alpha_alpha_conflicts
  - tests/unit/strata/test_access.py::TestModeConflict::test_write_conflicts_with_anything
  - tests/unit/strata/test_access.py::TestModeConflict::test_exclusive_conflicts_with_everything_including_itself
  - tests/unit/strata/test_access.py::TestModeConflict::test_append_conflicts_with_anything
  - tests/unit/strata/test_access.py::TestResourceContentionViolations::test_two_writers_no_arbiter_fires
  - tests/unit/strata/test_access.py::TestResourceContentionViolations::test_arbitrated_by_discharges
  - tests/unit/strata/test_access.py::TestResourceContentionViolations::test_lock_discharges
  - tests/unit/strata/test_access.py::TestResourceContentionViolations::test_read_only_modes_discharge_without_arbiter
  - tests/unit/strata/test_access.py::TestResourceContentionViolations::test_bare_resource_declaration_with_no_arbiter_still_fires
  - tests/unit/strata/test_access.py::TestResourceContentionViolations::test_single_accessor_never_fires
  - tests/unit/strata/test_access.py::TestResourceContentionViolations::test_unrelated_resources_do_not_cross_conflict
  - tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally
  - tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
  - strata-core/src/parse/mod.rs::tests::parses_node_access_clause
  - strata-core/src/parse/mod.rs::tests::parses_store_access_clause
  - strata-core/src/parse/mod.rs::tests::parses_all_access_modes
  - strata-core/src/parse/mod.rs::tests::error_access_rejects_unknown_mode
  - strata-core/src/parse/mod.rs::tests::error_access_requires_mode_keyword
  - strata-core/src/parse/mod.rs::tests::parses_resource_with_arbitrated_by
  - strata-core/src/parse/mod.rs::tests::parses_resource_with_lock
  - strata-core/src/parse/mod.rs::tests::parses_bare_resource_with_no_arbiter
  - strata-core/src/parse/mod.rs::tests::error_resource_rejects_both_arbitrated_by_and_lock
threat: null
component: null
---
Second half of the resource-contention mandate -- the grammar extension. Add: (1) access MODE on resource edges (owns/acl/stores gain mode=read|append|alpha|write|exclusive, default write for backward compat with current semantics -- decide and document). ALPHA SEMANTICS (user-specified 2026-07-22, the update/upgradeable-lock pattern): alpha declares INTEREST in a future writer lock; many writes need a read just before, so alpha sits between read and write. Compatibility matrix to encode and check: read+read OK; read+alpha OK (alpha never conflicts with readers); alpha+alpha CONFLICT (exactly one writer-intender per resource -- this is what prevents the two-readers-both-upgrading deadlock); alpha+write and write+anything CONFLICT; an alpha holder upgrades to write only once readers drain. (2) a shared-resource declaration with an ARBITER (resource NAME mode... arbitrated_by NODE|lock NAME) so two writers are provable-safe only through a declared arbiter/lease; (3) contention proof obligation: for every resource whose declared accessor modes violate the compatibility matrix (>1 writer-mode with no arbiter, OR >1 alpha declarant) a SYS error (fail-closed). parse.rs node/store symmetry per T-0261 precedent, tmLanguage update, docs/strata section, litmus fixtures. Field motivation: frob's own ledger-lock/refs-stash/info-exclude incidents -- repo-global resources with multiple writers and only convention as the arbiter. The mode-blind rules ship first in the sibling ticket; this upgrades them to mode-aware without renaming.