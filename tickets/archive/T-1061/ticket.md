---
id: T-1061
title: wire SYS205 mode-conformance into CLI dispatch + waiver channel + docs
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/sys_runner.py
- src/frob/gates/**
- docs/strata/host.md
- src/frob/gates/__init__.py
- src/frob/strata/_design_load.py
- tests/system/test_cli_sys_audit.py
- tests/test_gates.py
- docs/commands/sys.md
- docs/modules/gates.md
- docs/strata/surface.md
- design/frob.strata
- src/frob/strata/_mode_conformance.py
- src/frob/strata/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: check_mode_conformance needs (model, module, binding, root); DesignIds carries
    no Module/.resources field to source module from (mirrors store_ids' own precedent)
    -- narrowing gates/** to the exact SELFAUDIT001 call site (gates/__init__.py)
    per dispatch guidance
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_design_load.py
  reason: check_mode_conformance needs (model, module, binding, root); DesignIds carries
    no Module/.resources field to source module from (mirrors store_ids' own precedent)
    -- narrowing gates/** to the exact SELFAUDIT001 call site (gates/__init__.py)
    per dispatch guidance
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/system/test_cli_sys_audit.py
  reason: new SYS205 CLI wiring in sys_runner.py needs a system test asserting it
    fires via 'frob sys audit', mirroring the existing SYS2xx contention CLI test
    coverage in this file
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_gates.py
  reason: SELFAUDIT001's SYS205 fold needs a TestSelfAuditGate regression test, mirroring
    the existing SYS100-102/SYS2xx/REL2xx sub-family test coverage in this class
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/commands/sys.md
  reason: AFFECT001 names these as affects()-closure docs for _run_audit/_selfaudit_violations/DesignIds/load_design_ids,
    all genuinely changed by this ticket's SYS205 CLI+gate wiring and the new DesignIds.resources
    field
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/gates.md
  reason: AFFECT001 names these as affects()-closure docs for _run_audit/_selfaudit_violations/DesignIds/load_design_ids,
    all genuinely changed by this ticket's SYS205 CLI+gate wiring and the new DesignIds.resources
    field
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/strata/surface.md
  reason: AFFECT001 names these as affects()-closure docs for _run_audit/_selfaudit_violations/DesignIds/load_design_ids,
    all genuinely changed by this ticket's SYS205 CLI+gate wiring and the new DesignIds.resources
    field
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: wiring SYS205 live (SELFAUDIT001) surfaces a genuinely-new, first-turn-on
    finding against this repo's OWN five tickets_ledger write-mode accessors (no owns/acl
    path declared) -- needs a waived acknowledgment, same first-turn-on precedent
    T-1113's SYS104 mandatory flip already established
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_mode_conformance.py
  reason: wiring SYS205 live (SELFAUDIT001) discovers check_mode_conformance has NO
    waiver application at all -- the 5 tickets_ledger write-mode findings this surfaces
    on frob's own tree cannot be discharged any other way without an unrelated SYS201
    regression (owns= path declarations create 20 new overlapping-path findings, verified
    directly); real waiver support is required to land this safely
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_waive.py
  reason: wiring SYS205 live (SELFAUDIT001) discovers check_mode_conformance has NO
    waiver application at all -- the 5 tickets_ledger write-mode findings this surfaces
    on frob's own tree cannot be discharged any other way without an unrelated SYS201
    regression (owns= path declarations create 20 new overlapping-path findings, verified
    directly); real waiver support is required to land this safely
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_a_waived_sys205_finding_is_discharged_and_reported_waived
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_mode_conformance_violation
- tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_mode_nonconformance_exits_nonzero_with_named_gap
designated_repro_test: null
threat: null
component: null
---
T-0701 shipped `check_mode_conformance` (SYS205) as a pure, fully-tested
function in `src/frob/strata/_mode_conformance.py` -- CLI dispatch
(`frob sys audit`, `src/frob/app/sys_runner.py`) and the T-0174
`MULTI_INSTANCE_WAIVER_FAMILIES` waiver channel are both out of T-0701's
declared scope (`src/frob/strata/**`, `src/frob/vet/**`,
`tests/unit/strata/`), same disclosed-cut precedent
`_access.py`'s own SYS204 module docstring already used for T-0700. Also
wire the `docs/strata/host.md#resource-access-modes-t-0700` section (out
of scope for T-0701 too -- docs/strata/** is not in its scope globs) with
a new subsection documenting SYS205's per-mode semantics, the python-only
v0 detection scope, and the `lock`-only arbiter support.