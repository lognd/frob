---
id: T-2936
title: 'frob does not IMPORT on Windows: signal.SIGKILL evaluated as a default arg
  at module load crashes in 54s before any test runs'
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/_reap.py
- docs/modules/process.md
- src/frob/gates/__init__.py
- tests/unit/test_process_reap.py
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/process/_reap.py
  reason: fix signal.SIGKILL default-arg evaluated at import time
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/process.md
  reason: doc anchors for touched symbols
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/__init__.py
  reason: remove now-unnecessary explicit signal.SIGKILL call-site arg, defer to the
    safe internal default
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_process_reap.py
  reason: update fixtures + add must-fire/must-stay-quiet import-time repro tests
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/process.md
  reason: affects()-closure doc for arm_parent_death_signal / _arm_forkserver_helper_pdeathsig_if_requested
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/process.md
  reason: affects()-closure doc for arm_parent_death_signal / _arm_forkserver_helper_pdeathsig_if_requested
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/process.md
  reason: affects doc
  actor: logan
  at: '2026-08-26'
- op: add
  glob: frob.lock
  reason: frob ack writes here
  actor: logan
  at: '2026-08-26'
evidence:
- tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_default_arg_is_not_evaluated_at_def_time
- tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_sig_none_resolves_to_sigkill_only_after_the_platform_guard
- tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_noop_without_env_var
- tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_arms_when_env_var_set
designated_repro_test: tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_default_arg_is_not_evaluated_at_def_time
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
