---
id: T-1196
title: 'strata: multi-file design split with cross-file reference semantics'
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
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
evidence:
- tests/unit/strata/test_multifile.py::TestCheckCrossFileReferences::test_no_errors_when_all_resolve
- tests/unit/strata/test_multifile.py::TestCheckCrossFileReferences::test_missing_node_named_per_file
- tests/unit/strata/test_multifile.py::TestCheckCrossFileReferences::test_boundary_unknown_flow_named
- tests/unit/strata/test_multifile.py::TestMergeModules::test_concatenates_declarations
- tests/unit/strata/test_design_load.py::TestLoadIds::test_merges_ids
- tests/unit/strata/test_design_load.py::TestLoadIds::test_elaborate_failure_reported_with_store_ids_and_resources_intact
- tests/unit/strata/test_design_load.py::TestLoadIds::test_cross_file_flow_reference_resolves
- tests/unit/strata/test_multifile.py::TestElaborateMerged::test_resolves_cross_file_flow
- tests/unit/strata/test_design_load.py::TestLoadIds::test_cross_file_reference_to_missing_id_fails_closed
- tests/unit/strata/test_multifile.py::TestElaborateMerged::test_fails_closed_on_missing_id
designated_repro_test: null
acceptance:
- text: GIVEN design/frob.strata split into multiple .strata files under design/ WHEN
    frob check --only sys runs THEN elaboration resolves cross-file node/flow/boundary
    references identically to the single-file model (merged-model or explicit import
    mechanism, design decides) and gate findings are diff-clean vs the monofile
  evidence:
  - tests/unit/strata/test_design_load.py::TestLoadIds::test_cross_file_flow_reference_resolves
  - tests/unit/strata/test_multifile.py::TestElaborateMerged::test_resolves_cross_file_flow
- text: GIVEN a reference to a node declared in no loaded file THEN elaboration fails
    closed with a per-file error naming the missing id, not a silent partial model
  evidence:
  - tests/unit/strata/test_design_load.py::TestLoadIds::test_cross_file_reference_to_missing_id_fails_closed
  - tests/unit/strata/test_multifile.py::TestElaborateMerged::test_fails_closed_on_missing_id
threat: null
component: null
---
User directive 2026-07-29: design/frob.strata is 5588 lines and monolithic. _design_load.py (T-0080) already rglobs and loads every .strata file under design/, but elaboration produces one KernelModel PER FILE (DesignIds.models, one per file), so cross-file edges (flows/boundaries referencing nodes in another file) do not elaborate into one model today -- only merged id-surfaces (channels/boundaries/secrets/store_ids/resources) are unioned. Design question for the child design note: merge parsed Modules pre-elaboration into one KernelModel vs an explicit import/include construct in the surface grammar. Sibling ticket covers the attr interface= volume; splitting along component seams is only safe once cross-file references resolve.