---
id: T-1160
title: 'docs: document frob sys sync-interface in docs/commands/sys.md'
state: done
kind: docs
origin: agent
created: '2026-07-28'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- docs/commands/sys.md
- src/frob/app/sys_runner.py
- src/frob/strata/_sync_interface.py
- src/frob/strata/_plan.py
- src/frob/strata/_export.py
- src/frob/strata/_sysdoc.py
- src/frob/strata/_audit.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/sys_runner.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_sync_interface.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_plan.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_export.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_sysdoc.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_audit.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:uv run frob sys sync-interface --check exit=0 sha256=0a692ca85d0b
designated_repro_test: null
acceptance:
- text: GIVEN docs/commands/sys.md WHEN a reader looks up sys subcommands THEN sync-interface
    (and its --check mode) is documented with the SYS104-mandatory upkeep rationale
  evidence:
  - cmd:uv run frob sys sync-interface --check exit=0 sha256=0a692ca85d0b
threat: null
component: null
---
Refile of a T-1150 draft that died to ledger-restore cycles during its land (disclosed in the w18-strata3 done report): the new frob sys sync-interface subcommand landed (5103c0f1) but docs/commands/sys.md does not mention it.