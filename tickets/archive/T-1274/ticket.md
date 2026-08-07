---
id: T-1274
title: 'TEST005 burn-down: src/frob/app (115 findings, 63 at 0.0%)'
state: dropped
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/app/**
- tests/app/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN the app package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/app/**
  evidence: []
- text: GIVEN a 0.0%-branch symbol in app WHEN it is judged dead code THEN it is routed
    to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence: []
- text: GIVEN a new test added to close a app TEST005 finding WHEN reviewed THEN it
    asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence: []
threat: null
component: null
---
Package: src/frob/app (or the listed root modules).
TEST005 findings at current baseline: 115 total, 63 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
fleet_runner.py :: run
gitlog_runner.py :: run
vet_runner.py :: run
stats_runner.py :: run
arch_runner.py :: run
deprecated_runner.py :: run
telemetry.py :: is_disabled
telemetry.py :: iso_now
telemetry.py :: redact_command
telemetry.py :: append_event
telemetry.py :: tree_hash
telemetry.py :: estimate_tokens
telemetry.py :: record_cli_event
telemetry.py :: record_ticket_event
telemetry.py :: timed_call
perf_runner.py :: run
dup_runner.py :: run
xref_runner.py :: run
clean_runner.py :: run
_daemon_proxy.py :: ensure_daemon
_daemon_proxy.py :: query
_daemon_proxy.py :: _LeaseConnection.call
_daemon_proxy.py :: _LeaseConnection.close
_daemon_proxy.py :: try_daemon_lease
_daemon_proxy.py :: release_daemon_lease
worktree_runner.py :: run
parse_runner.py :: run
deploy_runner.py :: run
config.py :: AppConfig.from_external
config.py :: AppConfig.from_args
config.py :: load_arch_config
config.py :: stale_install_warning
scaffold_runner.py :: run
check_runner.py :: _ColorizedLevelFormatter.format
check_runner.py :: run
ack_runner.py :: run
doctor_runner.py :: run
natives_runner.py :: run
_snapshot.py :: load_or_build_snapshot
debt_runner.py :: run
... (23 more, see frob check --only test for the full list)

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.

## Drop reason
- 2026-07-29: duplicate: created twice due to script retry, T-1276 is canonical