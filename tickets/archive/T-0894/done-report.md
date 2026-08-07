## Done report

Built a shared signal, `frob.gates._registry_exhaustiveness.path_ever_tracked`
(git log -1 -- <path> against HEAD), that distinguishes "this repo never
adopted a registry" from "this repo adopted it and someone deleted it" --
the exact structural blind spot the ticket describes across all three
registry-backed gates that shared the old "missing dir/file means no
claim" posture. Wired it into registry_gate (REG012), compliance_gate
(COMPLIANCE006), and decisions_gate (DEC003), all unwaivable, all ERROR.
Updated docs/design/registry/EXHAUSTIVENESS-GATE.md (new REG012 section,
the canonical home for the mechanism), docs/modules/gates.md's
COMPLIANCE005 section, and docs/modules/decisions.md's DEC gates table to
close AFFECT001 on the three changed gate functions. Added regression
tests for all three (never-adopted stays silent, adopted-then-deleted
fires the new unwaivable rule) using synthetic tmp_path git repos.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestComplianceGate::test_compliance005_registered_in_known_gate_rules` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance006_silent_on_never_adopted_registry` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance006_fires_on_deleted_registry_after_adoption` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestPathEverTracked::test_never_committed_path_is_false` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestPathEverTracked::test_deleted_after_commit_is_true` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestPathEverTracked::test_git_failure_is_false` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestDeletedRegistry::test_never_adopted_registry_dir_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestDeletedRegistry::test_deleted_after_adoption_fires_reg012` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_never_adopted_decisions_dir_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_deleted_after_adoption_fires_dec003` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 0 error(s), 19388 warning(s), 333 waived
- error-findings: none (measured, zero errors)
