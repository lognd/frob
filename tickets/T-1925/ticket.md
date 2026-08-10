---
id: T-1925
title: design a ThreatViolation-to-boundary join for a boundary-scoped frob sys threats
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
- src/frob/strata/_threat.py
- src/frob/_cli_parsers/_misc.py
- src/frob/app/sys_runner.py
- src/frob/strata/__init__.py
- tests/unit/strata/test_threat.py
- docs/strata/threat.md
- docs/commands/sys.md
- tests/unit/test_app_sys_threats.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1925/**
  reason: explicit self-scope so SCOPE001's cross-ticket exemption (frob.gates._commit_exempts_file)
    recognizes this ticket's own shard commit and does not flag it against the filing
    ticket T-1480
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: tickets/T-1925/**
  reason: this self-scope grant never actually fixed SCOPE001 (frob.gates.__init__._TICKET_REF_RE
    only matches T-#### 4-digit ids in commit subjects, never a T-draft-<hex> id,
    so the cross-ticket exemption could never engage regardless) and land-parity already
    reports 0 unscoped errors without it; removing to reduce surface for the T-1918
    sibling-draft-finalize lease-collision land bug
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: T-1925 CLI wiring for frob sys threats plus its own test file and affects-doc
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: T-1925 CLI wiring for frob sys threats plus its own test file and affects-doc
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/__init__.py
  reason: T-1925 CLI wiring for frob sys threats plus its own test file and affects-doc
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: T-1925 CLI wiring for frob sys threats plus its own test file and affects-doc
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/strata/threat.md
  reason: T-1925 CLI wiring for frob sys threats plus its own test file and affects-doc
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/commands/sys.md
  reason: sys threats CLI docs live here
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_app_sys_threats.py
  reason: new integration test for the frob sys threats CLI wrapper
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/strata/test_threat.py::TestBoundaryScopeNodes::test_scope_is_flow_endpoints_plus_downstream_closure
- tests/unit/strata/test_threat.py::TestBoundaryScopeNodes::test_scope_stops_at_the_next_boundary
- tests/unit/strata/test_threat.py::TestBoundaryScopeNodes::test_unknown_boundary_id_fails_closed
- tests/unit/strata/test_threat.py::TestThreatViolationsForBoundary::test_filters_to_violations_on_nodes_in_scope
- tests/unit/strata/test_threat.py::TestThreatViolationsForBoundary::test_unknown_boundary_propagates_err
- tests/unit/test_app_sys_threats.py::TestSysThreats::test_no_boundary_prints_every_violation
- tests/unit/test_app_sys_threats.py::TestSysThreats::test_boundary_scopes_to_its_own_zone_only
- tests/unit/test_app_sys_threats.py::TestSysThreats::test_clean_model_reports_no_violations_and_exits_0
- tests/unit/test_app_sys_threats.py::TestSysThreats::test_unknown_boundary_id_exits_1
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
docs/strata/roadmap.md's "CLI surface (target)" names `frob sys threats
[boundary]` as a phase-5 verb. T-1480 investigated and found:
`frob.strata._threat.evaluate_threats` already computes the full
THREAT001-003 violation set, but a boundary-scoped filter needs a real
join from `ThreatViolation.node` to the boundary's flow endpoints that
does not exist anywhere yet -- more design work than a CLI wrapper (the
`trace` verb T-1480 built, by contrast, was a thin wrapper over the
already-shipped `FactBase.reachable`).

Needed before a CLI verb here is meaningful: design and implement the
node-to-boundary join. Filed as a residue of T-1480 rather than folded
into it, per that ticket's own scope note on why `threats` was cut.