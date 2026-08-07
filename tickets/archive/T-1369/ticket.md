---
id: T-1369
title: wire --allow-cross-ticket CLI flag for frob ticket land
state: done
kind: feature
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/_cli_parsers/_ticket.py
- src/frob/app/config.py
- tests/unit/test_ticket_runner_land_cmd_flags.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket.py
  reason: the flag needs a parser argument, an AppConfig field and its from_external
    mapping, plus a regression test
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/app/config.py
  reason: the flag needs a parser argument, an AppConfig field and its from_external
    mapping, plus a regression test
  actor: logan
  at: '2026-08-01'
- op: add
  glob: tests/unit/test_ticket_runner_land_cmd_flags.py
  reason: the flag needs a parser argument, an AppConfig field and its from_external
    mapping, plus a regression test
  actor: logan
  at: '2026-08-01'
evidence:
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestAllowCrossTicketReachesLand::test_land_receives_the_keyword[True]
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestAllowCrossTicketReachesLand::test_land_receives_the_keyword[False]
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestAllowCrossTicketReachesConfig::test_from_external_carries_the_flag
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestAllowCrossTicketFlagParsing::test_flag_sets_the_namespace_dest
designated_repro_test: null
threat: null
component: null
---
Found while working T-1355 (cross-ticket leakage preflight).

`land()` (src/frob/tickets/_land.py) now accepts `allow_cross_ticket:
bool = False`, the escape hatch for `_check_cross_ticket_leakage`'s new
refusal (a multi-ticket series worktree landing one ticket while
carrying a still-open sibling ticket's own committed work along with
it). The library-level parameter is fully implemented and tested, but no
CLI flag exists yet -- `frob ticket land` has no way to pass it through.

Suggested acceptance: add `--allow-cross-ticket` to `frob ticket land`'s
CLI (src/frob/app/ticket_runner/_land_cmd.py plus whatever argparse
wiring src/frob/_cli_parsers/** needs), threaded to `land(...,
allow_cross_ticket=...)`, with the same "logs a warning either way, never
silent" posture `--skip-mutation-evidence` already has.