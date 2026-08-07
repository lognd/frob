---
id: T-1319
title: 'perf-land follow-ups: restore 4 runner doc anchors, exhaustive dispatch-totality
  test'
state: done
kind: bug
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/app.md
- tests/unit/test_app_lazy_dispatch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app_lazy_dispatch.py::TestResolveRunnerDispatchTotality::test_every_non_bind_subcommand_resolves_a_callable_runner[bind]
- tests/unit/test_app_lazy_dispatch.py::TestResolveRunnerDispatchTotality::test_every_non_bind_subcommand_resolves_a_callable_runner[ticket]
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: GIVEN docs/modules/app.md THEN the frob:describes anchors and prose for doctor_runner.run,
    fleet_runner.run, registry_runner.run, worktree_runner.run (deleted by T-1216's
    commit with no rationale, their only documentation) are restored against the current
    lazy-dispatch reality
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- text: GIVEN tests/unit/test_app_lazy_dispatch.py THEN a parametrized test iterates
    EVERY Subcommand member asserting _resolve_runner resolves it (bind excepted by
    design), so a future subcommand added without a table entry fails statically instead
    of at first use
  evidence:
  - tests/unit/test_app_lazy_dispatch.py::TestResolveRunnerDispatchTotality::test_every_non_bind_subcommand_resolves_a_callable_runner[bind]
  - tests/unit/test_app_lazy_dispatch.py::TestResolveRunnerDispatchTotality::test_every_non_bind_subcommand_resolves_a_callable_runner[ticket]
threat: null
component: null
---
T-1206/T-1216 review 2026-07-29: both non-blocking APPROVE findings. Reviewer verified dispatch totality programmatically (34/34) so there is no live gap; this hardens it. The silent doc-anchor deletion is also a fresh instance of an ungated silent-miss shape (removing a frob:describes anchor from a doc leaves no finding when the doc file survives) -- note it on T-1232's status/currency mechanism as a candidate check: anchor-count regression on a doc file without an ack.