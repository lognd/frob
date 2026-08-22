---
id: T-2841
title: Fix I001 import-sort regression in T-2729's selfconform split (6 files)
state: done
kind: bug
origin: human
created: '2026-08-21'
priority: medium
parent: T-2373
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_selfconform.py
- src/frob/strata/_selfconform_binding_rules.py
- src/frob/strata/_selfconform_core_rules.py
- src/frob/strata/_selfconform_kinds.py
- src/frob/strata/_selfconform_models.py
- src/frob/strata/_selfconform_surface_rules.py
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: BUG002 land-time gate needs this directive for a pure import-reorder fix
    with no behavior delta
  actor: logan
  at: '2026-08-21'
  old_length: 357
  new_length: 674
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: given the 6 selfconform files with unsorted import blocks, when ruff --select
    I001 --fix runs and frob check runs unbudgeted repo-wide, then I001 reads zero
    findings everywhere, not just in these 6 files, and no SYS003/SYS100 undeclared-capability
    findings appear in these files
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 7cff575ae9b1423cf648eb4ee3d76c221aa9ff8a
---
T-2373 burned ruff I001 (import-sort) to zero and promoted it WARN->ERROR. T-2729's strata/_selfconform.py split (6 new modules) landed with unsorted import blocks, which the promoted-to-ERROR gate correctly caught as a regression the moment it appeared. Pure import reordering via ruff --select I001 --fix, zero behavior change. T-2729's agent has retired.

<!-- frob:no-behavior-change reason="Pure ruff --select I001 --fix import reordering across 6 files, zero logic/control-flow change. Verified via frob check unbudgeted: repo-wide I001=0, zero new SYS003/SYS100 findings in the touched files, and the same PERF004 findings that pre-existed the fix are unchanged." -->