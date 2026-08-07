---
id: T-0810
title: wire --force flag through to frob.tickets.archive's CLI entrypoint
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/__main__.py
- src/frob/app/config.py
- tests/test_ticket_runner*.py
- tests/test_tickets*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/__main__.py
  reason: T-0810 needs argparse wiring in __main__.py and an AppConfig field in config.py
    for --force, plus CLI test home; the T-0764 scope only covered tickets/**
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/config.py
  reason: T-0810 needs argparse wiring in __main__.py and an AppConfig field in config.py
    for --force, plus CLI test home; the T-0764 scope only covered tickets/**
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_ticket_runner*.py
  reason: T-0810 needs argparse wiring in __main__.py and an AppConfig field in config.py
    for --force, plus CLI test home; the T-0764 scope only covered tickets/**
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_tickets*.py
  reason: T-0810 needs argparse wiring in __main__.py and an AppConfig field in config.py
    for --force, plus CLI test home; the T-0764 scope only covered tickets/**
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_with_no_live_leases_stays_quiet
designated_repro_test: null
threat: null
component: null
---
T-0764 added archive(root, *, force: bool = False) in src/frob/tickets/__init__.py, refusing when a live cross-worktree lease exists unless force=True. The CLI entrypoint (_archive in src/frob/app/ticket_runner.py, 'frob ticket archive' subcommand) does not yet expose a --force flag to pass through, since that file is outside T-0764's declared scope (src/frob/tickets/**, tests/test_tickets*.py, tests/test_ticket_land.py). Add an argparse --force flag to the archive subcommand and thread it to archive(root, force=...).