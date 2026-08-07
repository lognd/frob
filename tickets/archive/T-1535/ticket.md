---
id: T-1535
title: 'frob check --land-parity: worktree mode evaluating exactly what the land sweep
  will (parity property-tested)'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/check_runner.py
- src/frob/_cli_parsers/_check.py
- tests/test_ticket_work_and_land_finish.py
- tests/system/test_cli_check.py
- docs/guides/agent-playbook.md
- docs/modules/tickets.md
- src/frob/app/config.py
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'T-1535 frob check --land-parity: worktree-mode land-sweep evaluation +
    parity test + playbook paragraph'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/check_runner.py
  reason: 'T-1535 frob check --land-parity: worktree-mode land-sweep evaluation +
    parity test + playbook paragraph'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/_cli_parsers/_check.py
  reason: 'T-1535 frob check --land-parity: worktree-mode land-sweep evaluation +
    parity test + playbook paragraph'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: 'T-1535 frob check --land-parity: worktree-mode land-sweep evaluation +
    parity test + playbook paragraph'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/system/test_cli_check.py
  reason: 'T-1535 frob check --land-parity: worktree-mode land-sweep evaluation +
    parity test + playbook paragraph'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: 'T-1535 frob check --land-parity: worktree-mode land-sweep evaluation +
    parity test + playbook paragraph'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-1535 frob check --land-parity: worktree-mode land-sweep evaluation +
    parity test + playbook paragraph'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/config.py
  reason: T-1535 needs a new AppConfig.check_land_parity field
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'T-1535: WIRE001 found check_land_parity missing from the CLI-arg passthrough
    tuple'
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestLandParityFindings::test_none_when_unmeasurable
- tests/test_ticket_work_and_land_finish.py::TestLandParityFindings::test_forces_no_gate_cache_env_on_the_spawn
- tests/test_ticket_work_and_land_finish.py::TestLandParityFindings::test_parity_with_the_land_sweeps_own_exemption_function
designated_repro_test: null
threat: null
component: null
---
Every blind repair round on 2026-08-04/05 came from worktree-check vs land-sweep divergence: DUP001 passed committed in the worktree but erred on the staged merge preview; gate caches hid findings until FROB_NO_GATE_CACHE=1; scoped --ticket runs skip the families that actually refuse lands (SELFAUDIT whole-design, diff-driven DUP, registry-level PII012). Deliver: (1) a --land-parity mode running the same unscoped errors-only evaluation _unscoped_error_findings performs, against the current tree, cache-bypassed, with the T-1524 checkpoint exemptions applied -- so an agent can converge in the worktree before the coordinator ever lands; (2) a parity property test: for a fixed tree, check --land-parity findings == the pre-commit sweep findings (same parser, same exclusions); (3) the agent playbook gains 'run --land-parity before writing your Done report'.