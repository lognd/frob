---
id: T-1834
title: frob sys export bypasses check_cross_file_references, can build a KernelModel
  with a dangling flow endpoint
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/sys_runner.py
- tests/unit/test_app_runners_batch7.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: add regression test for the dangling flow endpoint fix
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_app_runners_batch7.py::TestSysExport::test_dangling_flow_endpoint_fails_closed
designated_repro_test: null
threat: null
component: null
---
Found while deciding T-1521 (elaborate() itself should NOT gain flow src/dst validation -- see docs/strata/surface.md#multi-file-design-load-cross-file-references-t-1196 for why). sys_runner.py::_load_export_model calls elaborate() directly on a single parsed Module, never going through elaborate_merged/check_cross_file_references, so a flow naming an unknown node in an exported .strata file silently produces a KernelModel with a dangling flow endpoint instead of failing closed the way a design loaded under design/ would. Decide/implement a fix scoped to the export path (e.g. route single-file export through elaborate_merged) -- do not change elaborate()'s own permissive contract, which other tests rely on.