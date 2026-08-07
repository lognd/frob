---
id: T-0894
title: Registry-backed gates (COMPLIANCE005/REG*/DEC*) cannot distinguish never-adopted
  from deleted-registry
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_registry_exhaustiveness.py
- tests/test_gates.py
- tests/test_registry_exhaustiveness.py
- tests/test_decisions.py
- docs/design/registry/EXHAUSTIVENESS-GATE.md
- docs/modules/gates.md
- docs/modules/decisions.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: add regression tests for the adopted-then-deleted registry distinction (COMPLIANCE006/REG012/DEC003)
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_registry_exhaustiveness.py
  reason: add regression tests for the adopted-then-deleted registry distinction (COMPLIANCE006/REG012/DEC003)
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_decisions.py
  reason: add regression tests for the adopted-then-deleted registry distinction (COMPLIANCE006/REG012/DEC003)
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/design/registry/EXHAUSTIVENESS-GATE.md
  reason: T-0894 required doc updates for REG012/COMPLIANCE006/DEC003 to close AFFECT001
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: T-0894 required doc updates for REG012/COMPLIANCE006/DEC003 to close AFFECT001
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/decisions.md
  reason: T-0894 required doc updates for REG012/COMPLIANCE006/DEC003 to close AFFECT001
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates.py::TestComplianceGate::test_compliance005_registered_in_known_gate_rules
- tests/test_gates.py::TestComplianceGate::test_compliance006_silent_on_never_adopted_registry
- tests/test_gates.py::TestComplianceGate::test_compliance006_fires_on_deleted_registry_after_adoption
- tests/test_registry_exhaustiveness.py::TestPathEverTracked::test_never_committed_path_is_false
- tests/test_registry_exhaustiveness.py::TestPathEverTracked::test_deleted_after_commit_is_true
- tests/test_registry_exhaustiveness.py::TestPathEverTracked::test_git_failure_is_false
- tests/test_registry_exhaustiveness.py::TestDeletedRegistry::test_never_adopted_registry_dir_is_silent
- tests/test_registry_exhaustiveness.py::TestDeletedRegistry::test_deleted_after_adoption_fires_reg012
- tests/test_decisions.py::test_never_adopted_decisions_dir_is_silent
- tests/test_decisions.py::test_deleted_after_adoption_fires_dec003
designated_repro_test: null
acceptance:
- text: Given a repo that committed docs/design/registry/compliance.yaml and then
    deleted it, compliance_gate through its real production invocation FAILS (raises
    a COMPLIANCE006 Violation) before this ticket's fix and PASSES (returns the expected
    COMPLIANCE006 finding, proving the rule actually fires) after it -- test_compliance006_fires_on_deleted_registry_after_adoption
    exercises compliance_gate exactly as frob check dispatches it, not a pure-function
    unit test in isolation.
  evidence:
  - tests/test_gates.py::TestComplianceGate::test_compliance006_fires_on_deleted_registry_after_adoption
threat: null
component: null
---
Found while working T-0786 (gate-vacuousness sweep).

Several registry-backed gates share one "missing backing file/dir means no
claim, not a violation" posture, each independently justified in its own
docstring: `registry_gate` (REG001-011, src/frob/gates/_registry_exhaustiveness.py:812,
"if not base.is_dir(): ..."), `compliance_gate` (COMPLIANCE005,
src/frob/gates/__init__.py:7665, explicitly "matching registry_gate's own
missing-directory posture"), and `decisions_gate`'s DEC001/DEC002 half
(src/frob/gates/__init__.py:7035, "if not decisions_dir(root).exists():
return ()"). Each is individually reasonable ("a repo with no registry
makes no claim") but the aggregate effect is a real vacuousness vector none
of the three docstrings names: these YAML/markdown backing files, once a
repo HAS adopted them, become security/compliance-load-bearing artifacts
(COMPLIANCE005 in particular gates regulatory-control disposition
exhaustiveness) whose accidental or malicious DELETION is structurally
indistinguishable, to every one of these gates, from "this repo never
adopted the registry" -- both silently clear every violation the registry
existing would have produced. Nothing elsewhere in the gate catalog fires
on the deletion itself (no REF/DOC-family check treats
`docs/design/registry/compliance.yaml`'s disappearance as itself a
finding) once a repo has adopted the file.

Fix direction: for a repo that has ever adopted one of these registries
(a simple signal: the file/dir is present in the merge-base commit but
absent in the working tree, or a frob.toml flag marking the registry as
"required once adopted"), treat its disappearance as a loud, ideally
unwaivable violation rather than silently degrading to the "never adopted"
posture. Scope this ticket to at minimum COMPLIANCE005 (the
highest-stakes instance); REG*/DEC* can follow the same pattern once the
mechanism exists.