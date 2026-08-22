---
id: T-2813
title: 'Reformat batch 13/N: 13 files pending ruff-format (T-2359 child)'
state: done
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: T-2359
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/tickets/_doable.py
- src/frob/tickets/_land.py
- src/frob/tickets/_land_release.py
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_land_verify.py
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_renumber_v2.py
- src/frob/tickets/_store_migrate.py
- src/frob/tickets/_unlanded.py
- tests/unit/test_ticket_runner_land_cmd_flags.py
- tests/unit/test_ticket_runner_land_release.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestAllowCrossTicketFlagParsing::test_flag_sets_the_namespace_dest
- tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump::test_rewrites_version_and_prepends_changelog_entry
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 0fa8916ff354bc08c97fcca981aece506711ba08
---
Batch 13 of the T-2359 ruff-format-only reformat epic. 13 files re-measured against current main (b22f3adb6) via ruff format --check (45 files remaining before this batch). Format-only, no semantic changes. Excludes T-2373 historically-claimed test_ticket_land.py test_ticket_work_and_finish.py test_tickets_organization.py test_tickets_priority.py unit/test_app_runners_batch6.py unit/test_app_runners_t2395_contention.py and T-2806 tests/unit/test_check.py src/frob/gates/__init__.py