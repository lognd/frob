---
id: T-0415
title: 'perf: break single-threadpool GIL serialization -- overlap CPU-bound giants
  (process pool, ~77s wall)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0410
tier: ticket
sprint: null
scope:
- src/frob/check/
- src/frob/app/
- src/frob/gates/
- tests/test_gates.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestProcessPoolGates::test_process_job_runs_in_a_separate_process
- tests/test_gates.py::TestProcessPoolGates::test_combined_jobs_merge_in_canonical_order
- tests/test_gates.py::TestProcessPoolGates::test_run_gates_output_is_identical_across_repeated_runs
- tests/test_gates.py::TestProcessPoolGates::test_combined_parallel_path_matches_fully_serial_path
designated_repro_test: null
threat: null
component: null
---
docs/audits/perf.md H3. All 17 gates run in ONE ThreadPoolExecutor so under the GIL archgate(91.5s)+sys(77s) never overlap. FIX: run CPU-bound stages in a PROCESS pool (or make them cheap via shared parse) so they overlap. Measure wall before/after. Preserve T-0122 graph-built-once + no-swallowed-summary + deterministic output order.

NOTE (scope widened during implementation): the original `scope` declared
only `src/frob/check/` and `src/frob/app/`, but the H3 finding's actual
fix site -- the single `ThreadPoolExecutor` all 17 gates share -- is
`src/frob/gates/__init__.py:_run_jobs`/`_build_jobs`/`run_gates`, per this
ticket's own description and the audit citation
(`gates/__init__.py:3944`). `src/frob/check/`/`app/` only dispatch the
whole "gates" stage as one lumped task; they never see archgate/sys
individually, so the fix is undoable within the original scope. Widened
`scope` to add `src/frob/gates/` (the SCOPE001 gate's own suggested
remedy: "extend the ticket's scope or open a new ticket for this file")
rather than force a no-op change into check/app or silently touch gates/
unscoped. Also widened to `tests/test_gates.py` and `docs/modules/gates.md`
once SCOPE001 flagged those too (new tests + a doc-accuracy update for the
same change).