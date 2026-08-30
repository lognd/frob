---
id: T-3486
title: frob check stage groups do not cover the new land_parity and cross_ticket gates
  (T-3456/T-3466)
state: done
kind: bug
origin: agent
created: '2026-08-30'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/**
- docs/commands/check.md
- tests/system/test_cli_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on GitHub Actions run 33308245923 (ubuntu-latest, HEAD 355eb4468, 2026-08-30): suite completed in 16.3 min with 6 failures of 12816. Reproduce by node id with -p no:xdist first.

FAILING: tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
    assert frozenset({...}) <= frozenset({...})  -- the set of gates/tools is no longer covered by the available stage groups.
T-3456 added gate stage land_parity (LANDPARITY001/002) and T-3466 added CROSSTICKET001; neither was added to the check stage-group table that `frob check --only <stage>` and this test enumerate. Add them to the right stage group(s) (read src/frob/check for the stage table and docs/commands/check.md), and make the registration a single home if the gate list and the stage table are two copies (the test exists precisely because they desync).