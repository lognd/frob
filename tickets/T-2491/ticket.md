---
id: T-2491
title: sync docs/modules/app.md#runners for T-2486's structural --json stdout guard
state: queued
kind: docs
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2486 added _guard_json_stdout_writes (a structural boundary guard redirecting any stray stdout write to stderr during --json execution) and applied it in run()/_run_census()/_run_land_parity()/_run_stages_and_report()/_try_check_delta_via_daemon()/_run_ruff_fix_mode(), all in src/frob/app/check_runner.py. AFFECT001 flagged run and _run_census as needing their docs/modules/app.md#runners one-line index entries touched, but that file was held by T-2485's live cross-worktree scope lease at T-2486 land time, so T-2486 waived AFFECT001 there with a reason pointing at this ticket. Once T-2485 lands and the lease clears, add a short note to the check_runner.py::run / _run_census one-line entries (or a short blurb nearby) describing the new guard, mirroring what T-2486 already added to docs/modules/tickets-landing.md for _run_land_parity.