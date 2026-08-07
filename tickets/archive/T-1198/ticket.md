---
id: T-1198
title: 'strata: eliminate attr interface= boilerplate (4236 of 5588 frob.strata lines)
  via generated fragment or compact grammar'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- design/**
- docs/**
- tests/**
- strata-core/src/parse/**
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
scope_changes:
- op: add
  glob: strata-core/src/parse/**
  reason: T-1198's grammar shorthand (attr interface=[...]) is implemented in strata-core's
    Rust parser, not just the Python side
  actor: logan
  at: '2026-08-03'
evidence:
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_no_drift_reports_clean
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_legacy_form_migrated_even_with_matching_symbol_set
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_addition_and_removal_detected
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_store_block_missing_interface_attr_is_written
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_missing_interface_block_is_inserted_after_header
- tests/unit/strata/test_sync_interface.py::TestApplySyncInterface::test_writes_only_changed_files
designated_repro_test: null
acceptance:
- text: 'GIVEN the interface surface of a node WHEN it is machine-derivable (sync_interface
    already rewrites attr interface= lines to match code exactly) THEN the hand-authored
    .strata file no longer carries one line per symbol: either a generated .strata
    fragment (generate-and-verify like the rule registry) or a compact declaration
    form (list/module-ref) the parser accepts, design decides'
  evidence:
  - tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_no_drift_reports_clean
  - tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_legacy_form_migrated_even_with_matching_symbol_set
  - tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_addition_and_removal_detected
  - tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_store_block_missing_interface_attr_is_written
  - tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_missing_interface_block_is_inserted_after_header
  - tests/unit/strata/test_sync_interface.py::TestApplySyncInterface::test_writes_only_changed_files
- text: GIVEN the migration lands THEN frob check --only sys findings are diff-clean
    vs the inline-attr model and sync_interface round-trips idempotently on the new
    form
  evidence:
  - tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_no_drift_reports_clean
  - tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_legacy_form_migrated_even_with_matching_symbol_set
  - tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_addition_and_removal_detected
  - tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_store_block_missing_interface_attr_is_written
  - tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_missing_interface_block_is_inserted_after_header
  - tests/unit/strata/test_sync_interface.py::TestApplySyncInterface::test_writes_only_changed_files
threat: null
component: null
---
User directive 2026-07-29: 4236 of design/frob.strata's 5588 lines are attr interface=<symbol> lines, one symbol per line, maintained mechanically by frob.strata._sync_interface (which loads every .strata file and rewrites the attrs to match code exactly). The hand-authored design intent drowns in generated-shaped noise. Candidate designs for the design note: (a) generated sidecar fragment design/frob.interface.strata written by sync_interface and verified by the SYS gate (T-1008 generate-and-verify precedent); (b) grammar shorthand attr interface=[a, b, ...] or interface from <module-path> resolved at parse time; (c) move interface bindings out of the surface file entirely into the code-binding layer. Coordinate with T-1196 (multi-file split) -- a generated fragment is itself a second file, so the cross-file semantics land first or together.