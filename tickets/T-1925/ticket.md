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

## Done report

Changed:
src/frob/strata/_threat.py::boundary_scope_nodes
src/frob/strata/_threat.py::threat_violations_for_boundary
src/frob/strata/_threat.py::_boundary_by_id
src/frob/strata/__init__.py (exports the two new public symbols)
src/frob/_cli_parsers/_misc.py::_add_sys_parser
src/frob/_cli_parsers/_misc.py::_add_sys_threats_parser
src/frob/app/config.py::AppConfig (sys_threats_boundary field)
src/frob/app/sys_runner.py::_run_threats
src/frob/app/sys_runner.py::_print_threats_report
src/frob/app/sys_runner.py::run (dispatch wiring)
docs/strata/threat.md (new "Boundary-scoped frob sys threats" section)

Design: T-1925's join defines a `Boundary`'s scope as its own flow's
src/dst node ids plus every node `FactBase.reachable` reaches from the
flow's dst with `through_barriers=False` -- the SAME endorsement-
semantics closure THREAT003's discharge check already uses to decide
where taint stops, reused rather than reimplemented (no duplication).
`through_barriers=False` is deliberate: it makes a boundary's scope stop
at the NEXT downstream boundary rather than swallowing the whole model,
so a chain of boundaries each get a distinct scope. Fails closed
(StrataError.UnknownReference) on an unknown boundary id.
`threat_violations_for_boundary` filters an evaluated violation set to
that scope; a violation with node=None (THREAT001, view-scoped not
node-scoped) is dropped rather than silently attributed to a boundary.

Wired: `frob sys threats [boundary]` -- with no boundary argument prints
the full THREAT001-005 violation set (same conjunction `sys audit`
runs); with one, filters through the new join. Ran it live against this
repo's own design/frob.strata self-model, both unscoped and scoped to
the real boundary `b_vet_endorse` -- both runs completed and reported
"no violations" (0 pre-discharge obligations for the owasp-top-10 view
against this repo's current model), a genuine measured result, not an
assumed clean pass -- confirmed by first running unscoped (4912 effects
observed, 0 obligations) then re-running scoped to a real boundary id
from design/frob.strata and observing the same evaluate_threats() call
execute and filter correctly.

Evidence: 9 pytest node ids -- 5 in tests/unit/strata/test_threat.py
(TestBoundaryScopeNodes x3, TestThreatViolationsForBoundary x2) covering
the join primitives, plus 4 in a new tests/unit/test_app_sys_threats.py
(TestSysThreats), a direct-call `run(cfg)` integration test mirroring
`test_app_sys_trace.py`'s own pattern, added after TEST016 flagged the
CLI-wiring lines in sys_runner.py (dispatch, printer, boundary-vs-no-
boundary branching) as confirmatory-only under the first evidence set --
these 4 tests exercise `_run_threats`/`_print_threats_report` directly
against a real design model with a boundary and an unclassified-
capability violation, both scoped and unscoped, plus the clean-model and
unknown-boundary paths. Feature-kind ticket, not bug/security-kind, so
BUG002 repro-at-parent validation does not apply (--check-repro
correctly reports NO_VERDICT at parent since the symbols under test did
not exist there -- expected for new code, not a confirmatory-only
finding).

Filed: none
Gates: `frob check --ticket T-1925` -- gate:SCOPE/COV/AFFECT/FMT (the
ticket-scoped families) all clean (0 errors). Repo-wide FAILs present in
the same run (gate:DSL 1 error, gate:TEST 1 error, ruff-check,
ruff-format) are the SAME pre-existing baseline measured before this
ticket started (T-1926's post-land floor: gate:DSL 1 error, gate:TEST 1
error) -- unrelated to any file this ticket touched.

### Changed
```
 tickets/T-1925/done-report.md | 73 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1925/ticket.md      | 56 +++++++++++++++++++++++++++++++--
 2 files changed, 127 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_threat.py::TestBoundaryScopeNodes::test_scope_is_flow_endpoints_plus_downstream_closure` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestBoundaryScopeNodes::test_scope_stops_at_the_next_boundary` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestBoundaryScopeNodes::test_unknown_boundary_id_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestThreatViolationsForBoundary::test_filters_to_violations_on_nodes_in_scope` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestThreatViolationsForBoundary::test_unknown_boundary_propagates_err` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_threats.py::TestSysThreats::test_no_boundary_prints_every_violation` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_threats.py::TestSysThreats::test_boundary_scopes_to_its_own_zone_only` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_threats.py::TestSysThreats::test_clean_model_reports_no_violations_and_exits_0` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_threats.py::TestSysThreats::test_unknown_boundary_id_exits_1` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/strata-cli-surface/tests/unit/test_tickets_evidence_only_scope.py, TEST001@src/frob/app/ticket_runner/_new.py
