---
id: T-5470
title: 'WIRE002: three WIRE001 waivers name already-done follow-up tickets'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/unit/gates/test_wire002_live_repo.py::test_wire002_zero_against_live_repo

WIRE002 finds 3 stale WIRE001 waivers naming ALREADY-DONE follow-up
tickets:
- src/frob/testing/_dotnet_runner.py::run_dotnet_tests names T-4516
- src/frob/testing/_unity_batchmode.py::run_unity_batchmode names T-4516
- src/frob/webapp/_a11y_statement.py::_locate_statement_page names T-5454

Per WIRE002's own rule, a WIRE001 waiver must bind to a real, open
follow-up ticket; all three name tickets that are now done.

The first two files are in touch-scope and fixable here (repoint the
waiver to a new open follow-up ticket, or remove the waiver if the
underlying WIRE001 concern is now actually resolved). The third,
src/frob/webapp/_a11y_statement.py, is OUT of touch-scope (other-agent-
owned per this drain's brief) -- this test cannot go fully green without
that file also being fixed, so this ticket needs a partial fix here plus
hand-off of the webapp half to its owning agent.
