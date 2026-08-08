---
id: T-1843
title: wire find_policy_weakenings (INV-051) into a frob check gate over design/ policies
state: done
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_design_load.py
- src/frob/gates/_policy_weakening_gate.py
- src/frob/gates/__init__.py
- tests/unit/test_policy_weakening_gate.py
- design/frob.strata
- src/frob/gates/_waive.py
- docs/strata/policy.md
- docs/strata/surface.md
- docs/strata/host.md
- src/frob/strata/_policy.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_design_load.py
  reason: compile_policies needs the merged module.policies list, same pre-elaboration
    merge pattern as store_ids/resources; gate cannot call it without this
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/gates/**
  reason: 'narrow from 72-file glob to the exact files this ticket touches: new gate
    module, invariant-family wiring, DesignIds.policies merge helper, its unit tests,
    and this repo''s own design/frob.strata (INV-051 gate must run against it)'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/gates/_policy_weakening_gate.py
  reason: 'narrow from 72-file glob to the exact files this ticket touches: new gate
    module, invariant-family wiring, DesignIds.policies merge helper, its unit tests,
    and this repo''s own design/frob.strata (INV-051 gate must run against it)'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'narrow from 72-file glob to the exact files this ticket touches: new gate
    module, invariant-family wiring, DesignIds.policies merge helper, its unit tests,
    and this repo''s own design/frob.strata (INV-051 gate must run against it)'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/strata/_design_load.py
  reason: 'narrow from 72-file glob to the exact files this ticket touches: new gate
    module, invariant-family wiring, DesignIds.policies merge helper, its unit tests,
    and this repo''s own design/frob.strata (INV-051 gate must run against it)'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_policy_weakening_gate.py
  reason: 'narrow from 72-file glob to the exact files this ticket touches: new gate
    module, invariant-family wiring, DesignIds.policies merge helper, its unit tests,
    and this repo''s own design/frob.strata (INV-051 gate must run against it)'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: 'narrow from 72-file glob to the exact files this ticket touches: new gate
    module, invariant-family wiring, DesignIds.policies merge helper, its unit tests,
    and this repo''s own design/frob.strata (INV-051 gate must run against it)'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/gates/_waive.py
  reason: WIRE001 needs INV051 registered in _KNOWN_GATE_RULES; AFFECT001 needs the
    affects()-closure docs touched for the changed DesignIds/load_design_ids/policy_weakening_gate
    symbols
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/strata/policy.md
  reason: WIRE001 needs INV051 registered in _KNOWN_GATE_RULES; AFFECT001 needs the
    affects()-closure docs touched for the changed DesignIds/load_design_ids/policy_weakening_gate
    symbols
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/strata/surface.md
  reason: WIRE001 needs INV051 registered in _KNOWN_GATE_RULES; AFFECT001 needs the
    affects()-closure docs touched for the changed DesignIds/load_design_ids/policy_weakening_gate
    symbols
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/strata/host.md
  reason: WIRE001 needs INV051 registered in _KNOWN_GATE_RULES; AFFECT001 needs the
    affects()-closure docs touched for the changed DesignIds/load_design_ids/policy_weakening_gate
    symbols
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/strata/_policy.py
  reason: removed the now-obsolete WIRE001 waiver on find_policy_weakenings since
    this ticket gives it a real caller
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate::test_no_design_dir_noop
- tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate::test_weakening_detected
- tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate::test_clean_policies_no_finding
- tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate::test_load_failure_skips_silently
designated_repro_test: null
threat: null
component: null
---
T-1482 built find_policy_weakenings (src/frob/strata/_policy.py) as a pure TIER-1 diff pass over already-compiled CompiledPolicies, proving INV-051 (refinement monotonicity: a narrower-scope policy may only strengthen, never weaken, a confine_use/at_call_require_arg/mediate rule an containing policy already declares for the same target atom). It has no caller outside its own tests (WIRE001, waived on this ticket naming this follow-up). Wire it into a frob check gate that runs it over the real design/ policies loaded via load_design_ids/compile_policies, so a real weakening in design/frob.strata surfaces as a gate finding, not just an available-but-unused function.