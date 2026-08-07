---
id: T-0080
title: strata directives (frob:channel/boundary/secret) + SYS gates in run_gates
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0052
parent: T-0053
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/gates/**
- src/frob/strata/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_design_load.py::TestLoadIds::test_merges_ids
- tests/unit/strata/test_design_load.py::TestLoadIds::test_excluded_no_ids
designated_repro_test: null
threat: null
component: null
---
Call sites bind to kernel edges; SYS001.. family joins model, graph, and evidence in frob check with severity dial + waivers + remedies.
## Done report

frob:channel/frob:boundary/frob:secret verbs added to the comment DSL
(EdgeKind.CHANNEL/BOUNDARY/SECRET); load_design_ids parses+elaborates
every .strata file under design/ (or [strata].design_dir), RESPECTING
the shared frob.excludes leaf so excluded example models carry no
obligations; sys gate: SYS001 (ERROR, dangling directive reference --
suppressed whenever any design file failed to load), SYS002 (WARN,
boundary/secret-clearance node with no code binding), SYS003 (WARN,
warn-first per COV001 precedent, tier-2 import conformance surfaced),
SYS004 (ERROR, design file failed to parse -- the honest diagnostic
instead of fake danglings). Opt-in: no design dir, no gate. Review
round 1 REJECTed on exclude-leaf wiring, parse-failure false positives,
and SYS003 severity; all three fixed and re-verified (frob check --only
sys = 0 violations on this repo). Verified at merge on main: 135 tests
across design-load/graph/gates suites; a cherry-pick dropped the
dsl/_models hunks initially, recovered from the worktree and verified
by the same suites.