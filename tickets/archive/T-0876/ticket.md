---
id: T-0876
title: wire frob exports --consumers CLI flag onto exports_consumers
state: done
kind: feature
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/exports_runner.py
- src/frob/app/config.py
- src/frob/__main__.py
- docs/commands/exports.md
- tests/unit/test_app_runners.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_runners.py
  reason: CLI-level tests for --consumers wiring live here
  actor: logan
  at: '2026-07-26'
evidence:
- tests/unit/test_app_runners.py::TestExportsRunner::test_consumers_mode_logs_result
- tests/unit/test_app_runners.py::TestExportsRunner::test_consumers_mode_json_output
- tests/unit/test_app_runners.py::TestExportsRunner::test_consumers_mode_err_result_exits_1
designated_repro_test: null
threat: null
component: null
---
Follow-on to T-0858's xref-sunset reevaluation. `frob.exports.exports_consumers`
(added by T-0858) answers "who imports this symbol" as a library function, but
there is no CLI entry point yet -- wiring `frob exports --consumers <symbol>`
(or a dedicated verb) requires touching src/frob/app/exports_runner.py,
src/frob/app/config.py, and src/frob/__main__.py's exports parser, none of
which were in T-0858's declared scope. Do this before or around the
2026-10-01 T-0802 sunset so the CLI-level capability is not lost when
`frob xref` porcelain is removed.