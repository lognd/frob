---
id: T-1176
title: 'gates: named waiver presets -- frob:waive RULE preset=<name> resolving to
  one documented reason text'
state: done
kind: ux
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
- src/frob/graph/**
- tests/test_gates.py
- design/frob.strata
- src/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/graph/**
  reason: 'The preset mechanism must live where frob:waive is parsed (frob.graph.dsl,

    plus a new frob.graph._waive_presets module) since frob.gates depends on

    frob.graph, not the reverse; its drift-lock test lives in tests/test_gates.py

    alongside the existing waiver test classes. SYS104 requires design/frob.strata

    to track the two new public graphlang symbols (WAIVE_PRESETS, resolve_preset)

    and the new TestWaivePresets testsuite symbol in the same land -- frob sys

    sync-interface writes only that file. Acceptance[1] requires migrating the

    repo-wide INV006 calibration-batch and REF002 split-fragment verbatim waiver

    copies to the new preset, which are scattered across src/** by construction

    (each site''s own file carries its own copy) -- widening to src/** covers

    exactly those comment-only migrations, no other src/** work is in scope.

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_gates.py
  reason: 'The preset mechanism must live where frob:waive is parsed (frob.graph.dsl,

    plus a new frob.graph._waive_presets module) since frob.gates depends on

    frob.graph, not the reverse; its drift-lock test lives in tests/test_gates.py

    alongside the existing waiver test classes. SYS104 requires design/frob.strata

    to track the two new public graphlang symbols (WAIVE_PRESETS, resolve_preset)

    and the new TestWaivePresets testsuite symbol in the same land -- frob sys

    sync-interface writes only that file. Acceptance[1] requires migrating the

    repo-wide INV006 calibration-batch and REF002 split-fragment verbatim waiver

    copies to the new preset, which are scattered across src/** by construction

    (each site''s own file carries its own copy) -- widening to src/** covers

    exactly those comment-only migrations, no other src/** work is in scope.

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: 'The preset mechanism must live where frob:waive is parsed (frob.graph.dsl,

    plus a new frob.graph._waive_presets module) since frob.gates depends on

    frob.graph, not the reverse; its drift-lock test lives in tests/test_gates.py

    alongside the existing waiver test classes. SYS104 requires design/frob.strata

    to track the two new public graphlang symbols (WAIVE_PRESETS, resolve_preset)

    and the new TestWaivePresets testsuite symbol in the same land -- frob sys

    sync-interface writes only that file. Acceptance[1] requires migrating the

    repo-wide INV006 calibration-batch and REF002 split-fragment verbatim waiver

    copies to the new preset, which are scattered across src/** by construction

    (each site''s own file carries its own copy) -- widening to src/** covers

    exactly those comment-only migrations, no other src/** work is in scope.

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/**
  reason: 'The preset mechanism must live where frob:waive is parsed (frob.graph.dsl,

    plus a new frob.graph._waive_presets module) since frob.gates depends on

    frob.graph, not the reverse; its drift-lock test lives in tests/test_gates.py

    alongside the existing waiver test classes. SYS104 requires design/frob.strata

    to track the two new public graphlang symbols (WAIVE_PRESETS, resolve_preset)

    and the new TestWaivePresets testsuite symbol in the same land -- frob sys

    sync-interface writes only that file. Acceptance[1] requires migrating the

    repo-wide INV006 calibration-batch and REF002 split-fragment verbatim waiver

    copies to the new preset, which are scattered across src/** by construction

    (each site''s own file carries its own copy) -- widening to src/** covers

    exactly those comment-only migrations, no other src/** work is in scope.

    '
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_gates.py::TestWaivePresets::test_docs_table_matches_waive_presets
- tests/test_gates.py::TestWaivePresets::test_resolve_preset_known_name
- tests/test_gates.py::TestWaivePresets::test_resolve_preset_unknown_name_is_none
- tests/test_gates.py::TestWaivePresets::test_waive_preset_resolves_reason_and_matches_like_inline
- tests/test_gates.py::TestWaivePresets::test_unknown_preset_is_malformed_directive
designated_repro_test: null
acceptance:
- text: GIVEN a frob:waive directive using preset=<name> WHEN gates evaluate it THEN
    the reason resolves from a single documented preset table (docs/modules/gates.md
    section, machine-read), behaves identically to the inline reason, and an unknown
    preset name is an error
  evidence:
  - tests/test_gates.py::TestWaivePresets::test_waive_preset_resolves_reason_and_matches_like_inline
  - tests/test_gates.py::TestWaivePresets::test_unknown_preset_is_malformed_directive
  - tests/test_gates.py::TestWaivePresets::test_docs_table_matches_waive_presets
- text: GIVEN the existing calibration-batch INV006 text THEN it becomes preset=split-carried-prose
    and the repo's 10+ verbatim copies are migrated to it in the same land
  evidence:
  - tests/test_gates.py::TestWaivePresets::test_resolve_preset_known_name
threat: null
component: null
---
User directive 2026-07-29: remove boilerplate agents hand-write. The 8-line INV006 calibration-batch waiver text has been copy-pasted 10+ times this drive (0abc4e3a lineage), and the T-1099 REF002 split-fragment text 7+ times. A preset is NOT a blanket waiver: each site still carries an explicit per-site directive naming rule + preset; the preset only deduplicates the REASON prose, which the NO DUPLICATION principle applies to as much as code. Reason-required stays intact -- a preset name must resolve to a real documented reason.