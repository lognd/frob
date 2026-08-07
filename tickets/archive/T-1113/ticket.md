---
id: T-1113
title: 'strata: promote SYS104/105/106 to mandatory + add CHK-GATE-SYS104/105/106
  registry entries'
state: done
kind: security
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
- docs/design/registry/check-coverage.yaml
- src/frob/strata/_selfconform.py
- docs/modules/strata.md
- tests/unit/strata/test_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/strata.md
  reason: SYS104 flip needs test updates (opt-in-only test now stale) and the SYS104/105/106
    doc sections need the mandatory-flip wording, mirroring the SYS103/T-0667 doc
    precedent
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: SYS104 flip needs test updates (opt-in-only test now stale) and the SYS104/105/106
    doc sections need the mandatory-flip wording, mirroring the SYS103/T-0667 doc
    precedent
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_node_with_no_interface_attr_is_never_checked
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_node_with_empty_real_surface_stays_exempt
- tests/unit/strata/test_selfconform.py::TestUnmodeledCodeMissingPackageRoot::test_missing_package_root_produces_no_warning
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
designated_repro_test: null
threat: null
component: null
---
SYS104 (T-0668, src/frob/strata/_selfconform.py) only evaluates a node
that has already declared at least one `interface=` attr -- an opt-in
scope cut, disclosed in T-0668's Done report, because making it
mandatory repo-wide would require adding `interface=` declarations to
`design/frob.strata`, which was outside T-0668's declared scope
(`src/frob/strata/**`, `src/frob/graph/**`, `docs/modules/strata.md`,
`tests/unit/strata/**` -- not `design/frob.strata`).

Two follow-ups bundled here (same shape as SYS103's own T-1079-class
deferred work):
1. Add real `interface=` declarations to `design/frob.strata`'s nodes
   (measured against each node's actual public surface,
   `_module_public_symbols`), then flip SYS104 to fire on ANY node
   whose bound code has a public symbol, not just opt-in nodes.
2. Add `CHK-GATE-SYS104`/`CHK-GATE-SYS105`/`CHK-GATE-SYS106` entries to
   `docs/design/registry/check-coverage.yaml` and the corresponding
   `frob:enforces` directives on `check_self_conformance`, mirroring the
   `CHK-GATE-SYS103` precedent (T-0667's Done report's own deferred
   registry gap, `docs/modules/strata.md#known-gap-registry-cross-
   reference`) -- `docs/design/registry/**` was outside T-0668/T-0669/
   T-0670's declared scope.