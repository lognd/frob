---
id: T-2285
title: Extend T-2280's file-local pre-land error gate to DOC005/SELFAUDIT001/ARCH103
state: done
kind: feature
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: new DOC005 checker + tests live in the module's existing land test file
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrorsDoc005::test_a_new_stale_row_refuses_the_land
- tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrorsDoc005::test_a_pre_existing_stale_row_merely_touched_does_not_refuse
- tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrorsDoc005::test_no_docblocks_config_is_a_no_op
- tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_a_new_render001_refuses_the_land
- tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_new_over_threshold_function_refuses_the_land
designated_repro_test: tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrorsDoc005::test_a_new_stale_row_refuses_the_land
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 45e025ef7c320b97ab87bb89075342f681003cbd
---
T-2280 generalized T-2214's does-not-worsen land-time gate to a severity-derived registry of FILE-LOCAL ERROR checkers (RENDER001 registered). Three rules named in T-2280's own measured evidence (RENDER001 1->4, SELFAUDIT001 1->3, DOC005 2->3, ARCH103 2->3) do NOT fit the file-local (current-content vs merge-base-content, two small parses) shape: DOC005 targets README.md/the CLI table specifically and compares against the parser tree, not the file's own prior content; SELFAUDIT001 evaluates frob's own design/compliance state, not any particular touched file; ARCH103 needs the repo-wide call graph for SRP/cohesion classification. Bringing these under land-time coverage needs either (a) a bounded, cheap way to compute each without a full analyze_project/GraphSnapshot build, or (b) accepting a different, still-bounded cost model than T-2280's two-parses-per-file one. Scoped follow-up, not a widening of T-2280 itself.