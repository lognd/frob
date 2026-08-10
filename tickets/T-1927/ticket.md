---
id: T-1927
title: design a population/date-projected capacity evaluator for frob sys capacity
state: done
kind: feature
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_capacity.py
- src/frob/strata/__init__.py
- docs/strata/reliability.md
- src/frob/_cli_parsers/_misc.py
- src/frob/app/sys_runner.py
- docs/commands/sys.md
- tests/unit/strata/test_capacity_projection.py
- src/frob/app/_config_external.py
- tests/unit/test_app_sys_capacity.py
- tickets/T-2016/ticket.md
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1927/**
  reason: explicit self-scope so SCOPE001's cross-ticket exemption (frob.gates._commit_exempts_file)
    recognizes this ticket's own shard commit and does not flag it against the filing
    ticket T-1480
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: tickets/T-1927/**
  reason: this self-scope grant never actually fixed SCOPE001 (frob.gates.__init__._TICKET_REF_RE
    only matches T-#### 4-digit ids in commit subjects, never a T-draft-<hex> id,
    so the cross-ticket exemption could never engage regardless) and land-parity already
    reports 0 unscoped errors without it; removing to reduce surface for the T-1918
    sibling-draft-finalize lease-collision land bug
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: src/frob/strata/**
  reason: T-1927 is the new _capacity.py module plus its package export and doc anchor
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_capacity.py
  reason: T-1927 is the new _capacity.py module plus its package export and doc anchor
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/__init__.py
  reason: T-1927 is the new _capacity.py module plus its package export and doc anchor
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/strata/reliability.md
  reason: T-1927 is the new _capacity.py module plus its package export and doc anchor
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/strata/test_capacity.py
  reason: CLI wiring for frob sys capacity plus its unit test file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: CLI wiring for frob sys capacity plus its unit test file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: CLI wiring for frob sys capacity plus its unit test file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/commands/sys.md
  reason: CLI wiring for frob sys capacity plus its unit test file
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: tests/unit/strata/test_capacity.py
  reason: fix scope typo -- new tests live in test_capacity_projection.py, not the
    pre-existing test_capacity.py
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/strata/test_capacity_projection.py
  reason: fix scope typo -- new tests live in test_capacity_projection.py, not the
    pre-existing test_capacity.py
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/_config_external.py
  reason: float CLI flags need an explicit _FLOAT_FIELDS allowlist entry for --population
    to actually reach AppConfig
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_app_sys_capacity.py
  reason: T-1927 integration test file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-2016/ticket.md
  reason: residue ticket filed mid-ticket via frob ticket new; scope covers its own
    auto-committed file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_waive.py
  reason: CAP001 must be registered in _KNOWN_GATE_RULES before this ticket can close
    (T-1937 UnregisteredGateRuleConstructed guard)
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_over_capacity_current_demand_fires
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_within_capacity_is_clean
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_node_with_no_capacity_declared_is_never_checked
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_capacity_scales_with_replicas_max_unlike_rel380
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_population_scales_demand_linearly
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_population_with_no_baseline_fails_closed
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_baseline_population_reported_on_report
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_no_users_anywhere_baseline_is_none
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_no_population_reports_current_violations
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_population_scales_and_can_fire
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_no_violations_exits_0
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_population_with_no_baseline_exits_1
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_population_flag_survives_real_argv_parsing
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
docs/strata/roadmap.md's "CLI surface (target)" names `frob sys capacity
[--population N | --at DATE]` as a phase-5 verb. T-1480 investigated and
found: no existing evaluator projects capacity thresholds against a
POPULATION or DATE parameter at all (`_starvation.py`'s capacity checks
are static, not projected) -- this is new modeling work, not a CLI-glue
gap over an existing evaluator (unlike `trace`, which T-1480 built as a
thin wrapper over the already-shipped `FactBase.reachable`).

Needed before a CLI verb here is meaningful: a real
population/date-projected capacity evaluator in `frob.strata`, analogous
to how `FactBase.reachable`/`propagated_demand` already model influence
closure and load propagation. Filed as a residue of T-1480 rather than
folded into it, per that ticket's own scope note on why `capacity` was
cut.