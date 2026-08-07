---
id: T-0562
title: add missing frob:ticket coverage markers for T-0461 runner changes
state: done
kind: docs
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/bind_runner.py
- src/frob/app/dup_runner.py
- src/frob/app/mutate_runner.py
- src/frob/app/perf_runner.py
- src/frob/app/release_runner.py
- src/frob/app/stats_runner.py
- src/frob/app/sys_runner.py
- src/frob/app/vet_runner.py
- tests/unit/test_app_runners_batch5.py
- tests/system/test_cli_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_runners_batch5.py
  reason: T-0562 evidence lives in these shared runner test modules
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/system/test_cli_vet.py
  reason: T-0562 evidence lives in these shared runner test modules
  actor: logan
  at: '2026-07-21'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/unit/test_app_runners_batch5.py::TestBindRunner::test_list_bindings_text_mode
- tests/system/test_cli_vet.py::TestHookMode::test_old_package_passes
designated_repro_test: null
threat: null
component: null
---
found while working T-0459: T-0461's render-migration edits to these runner functions never got a frob:ticket edge, so COV002 fires once T-0461 closed (scope-grace only covers OPEN tickets). This ticket adds the frob:ticket marker to each touched symbol so COV002 clears without reopening T-0461.