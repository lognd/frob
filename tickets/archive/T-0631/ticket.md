---
id: T-0631
title: 'frob ticket land: TICK005-backed regression sweep + --push option'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0577
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
- src/frob/__main__.py
- src/frob/app/config.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/__main__.py
  reason: 'The --push option''s acceptance criterion requires a real, working

    `frob ticket land --push` CLI flag. The argparse registration for

    `frob ticket land` lives in src/frob/__main__.py, and the flag needs a

    backing AppConfig field in src/frob/app/config.py (same pattern as the

    existing --dry-run/--skip-mutation-evidence flags on this same

    subcommand). T-0631''s declared scope (src/frob/tickets/**,

    src/frob/app/ticket_runner.py, docs/modules/tickets.md) omits both files,

    which makes the --push half of this ticket''s plan undoable as scoped.

    Adding exactly these two files, narrowly, to implement the one new flag

    this ticket''s acceptance criteria requires.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: src/frob/app/config.py
  reason: 'The --push option''s acceptance criterion requires a real, working

    `frob ticket land --push` CLI flag. The argparse registration for

    `frob ticket land` lives in src/frob/__main__.py, and the flag needs a

    backing AppConfig field in src/frob/app/config.py (same pattern as the

    existing --dry-run/--skip-mutation-evidence flags on this same

    subcommand). T-0631''s declared scope (src/frob/tickets/**,

    src/frob/app/ticket_runner.py, docs/modules/tickets.md) omits both files,

    which makes the --push half of this ticket''s plan undoable as scoped.

    Adding exactly these two files, narrowly, to implement the one new flag

    this ticket''s acceptance criteria requires.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'SCOPE001 flags tests/test_ticket_land.py as outside declared scope; this

    ticket''s own new regression-sweep/--push behavior needs test coverage in

    the existing land test module (same file every prior land-feature ticket

    in this lineage, e.g. T-0755/T-0844/T-0907, has extended). Adding it.

    '
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_ticket_land.py::TestTick005LandRegressions::test_no_regression_when_terminal_ticket_stays_terminal
- tests/test_ticket_land.py::TestTick005LandRegressions::test_detects_terminal_ticket_regressed_to_non_terminal
- tests/test_ticket_land.py::TestTick005LandRegressions::test_archived_ids_are_excluded
- tests/test_ticket_land.py::TestTick005LandRegressions::test_malformed_text_degrades_to_no_regressions
- tests/test_ticket_land.py::TestLandRefusesOnTerminalStateRegression::test_land_refuses_and_unwinds_when_sweep_finds_a_regression
- tests/test_ticket_land.py::TestLandPushCliWiring::test_flag_parses_to_true
- tests/test_ticket_land.py::TestLandPushCliWiring::test_flag_omitted_defaults_false
- tests/test_ticket_land.py::TestPushAfterLand::test_dry_run_never_pushes
- tests/test_ticket_land.py::TestPushAfterLand::test_real_land_pushes_the_current_branch
- tests/test_ticket_land.py::TestPushAfterLand::test_push_failure_exits_nonzero
- tests/test_ticket_land.py::TestPushAfterLand::test_exec_disabled_exits_nonzero
designated_repro_test: null
acceptance:
- text: GIVEN a land with --push WHEN the land completes THEN the push happens only
    after every land verification passed; GIVEN the TICK005 rule defined WHEN land
    runs THEN the regression sweep executes and blocks on failure
  evidence:
  - tests/test_ticket_land.py::TestLandRefusesOnTerminalStateRegression::test_land_refuses_and_unwinds_when_sweep_finds_a_regression
  - tests/test_ticket_land.py::TestPushAfterLand::test_real_land_pushes_the_current_branch
threat: null
component: null
---
The two T-0577 dispatch items that had no existing design to build against, deferred honestly rather than half-built: (1) a TICK005-backed regression sweep at land time (define the TICK005 rule first, then have land run it); (2) a --push option for frob ticket land so the coordinator can land+push in one verified step. NOTE: T-0577's Done report references this as T-draft-f6f10c67; that draft was filed pre-fix and will not survive T-0577's own land, so this is the real ticket.