---
id: T-0630
title: 'strata: wire real code binding into production discharge entrypoints so G1
  fail-closed actually fires'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0595
parent: T-0401
tier: ticket
sprint: null
scope:
- src/frob/strata/_audit.py
- src/frob/strata/_sysdoc.py
- src/frob/strata/_plan.py
- src/frob/vet/_containment.py
- tests/unit/strata/
- tests/test_vet_containment.py
- pyproject.toml
- uv.lock
- CHANGELOG.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_vet_containment.py
  reason: T-0630's own binding/root wiring in vet/_containment.py makes the CONTAINED-finding
    fixture's discharge check real (G1 code-bound join); the fixture needed a genuine
    parameterization() call site to keep discharging honestly -- fixing it is a direct,
    narrow consequence of the ticket's own change, not new work
  actor: logan
  at: '2026-07-22'
- op: add
  glob: pyproject.toml
  reason: REL001 requires a version bump + changelog entry for this ticket's public
    API change (evaluate_exhaustiveness/render_audit_matrix/plan_obligations/build_containment_report
    gained binding/root params); uv.lock is regenerated mechanically alongside pyproject.toml's
    version bump
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: REL001 requires a version bump + changelog entry for this ticket's public
    API change (evaluate_exhaustiveness/render_audit_matrix/plan_obligations/build_containment_report
    gained binding/root params); uv.lock is regenerated mechanically alongside pyproject.toml's
    version bump
  actor: logan
  at: '2026-07-22'
- op: add
  glob: CHANGELOG.md
  reason: REL001 requires a version bump + changelog entry for this ticket's public
    API change (evaluate_exhaustiveness/render_audit_matrix/plan_obligations/build_containment_report
    gained binding/root params); uv.lock is regenerated mechanically alongside pyproject.toml's
    version bump
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/strata/test_audit.py::TestCodeBoundWiring::test_root_wires_real_code_binding_and_surfaces_threat003
- tests/unit/strata/test_audit.py::TestCodeBoundWiring::test_root_with_real_call_site_still_proves_clean
- tests/unit/strata/test_audit.py::TestCodeBoundWiring::test_no_root_preserves_pre_t0630_model_only_posture
- tests/test_vet_containment.py::TestBuildContainmentReport::test_contained_finding_when_obligation_discharged
designated_repro_test: null
acceptance:
- text: GIVEN a fixture repo whose ENDORSE boundary predicate has no observed call
    site WHEN the production strata audit gate runs (not a unit test) THEN the THREAT003
    unbound-boundary violation appears in frob check/sys audit output
  evidence: []
threat: tampering
component: null
---
T-0595 added the ENDORSE-boundary code-binding join (observed_call_names + _predicate_is_code_bound threaded through check_discharge_completeness) but every production caller (_audit.py / frob sys audit, _sysdoc.py, _plan.py, vet/_containment.py, _pii.py, _compliance.py) omits the optional binding/root arguments, so the fail-closed path never engages outside the new unit tests -- enforcement exists but nothing invokes it (the catalogued-is-not-enforced trap). Wire the real code tree into each production entrypoint so an unbound sanitizer predicate fails the actual gate, with an integration test proving frob sys audit (or equivalent) reports the THREAT003 on a fixture repo. Disclosed-but-unticketed cut from T-0595's Done report; this is the real ticket.