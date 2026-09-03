## Done report

Root cause: `policy_weakening_gate` (src/frob/gates/_policy_weakening_gate.py)
built every INV051 `Violation` with `file=design_dir` (the constant "design"),
the same anchor-collapse defect T-3419 fixed generically for SELFAUDIT001.
Unlike SELFAUDIT001, INV051's message names policy ids (child_id/parent_id),
never a real file path, so T-3419's generic message-text-extraction fix
cannot recover a distinguishing file for it -- confirmed by T-3419's own
Done report, which filed this ticket as the necessary gate-side follow-up.

Fix: `_policy_id_file_map(root, design_dir)` re-walks every `.strata` file
under the design dir (duplicating `frob.gates._vmodel._strata_files`'s own
file walk, T-0135 posture -- same reasoning that module already documents
for not cross-importing) and re-parses each one (cheap: `frob.strata` is
already imported by this point) to build a `{policy_id: rel_file}` map --
the same `node_file`-map pattern `frob.gates._vmodel._vmodel_violations`
already uses for VMOD001 (T-3264, the ticket's own cited precedent).
`DesignIds.policies` itself cannot answer this: it merges every file's
`PolicyDecl`s into one flat tuple, discarding which file declared which
(see that dataclass's own docstring). Each finding's `Violation.file` is
now `policy_file.get(weakening.child_id, design_dir)` -- the real
declaring file when resolvable, degrading unchanged to the pre-fix shared
anchor otherwise (never raises, never drops the finding).

Confirmed the must-fire fixture fails on unpatched code (reverted the fix
locally, re-ran the test: two weakenings in two different files both
collapsed to `("INV051", "design")` instead of resolving to their own
files; restored after confirming) and passes with the fix.

Tests: 7/7 pass in tests/unit/test_policy_weakening_gate.py (-p no:xdist)
-- 3 new (must-fire, single-file-real-path control, unresolvable-fallback
control) plus 4 pre-existing siblings re-run as regression controls.

### Changed
```
 tickets/T-3460/ticket.md | 10 +++++++++-
 1 file changed, 9 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGateFileIdentity::test_must_fire_two_weakenings_in_different_files_get_distinct_file_identities` (pytest node id, verified passing when recorded)
- `tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGateFileIdentity::test_single_file_weakening_reports_that_real_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGateFileIdentity::test_unresolvable_child_id_falls_back_to_design_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate::test_weakening_detected` (pytest node id, verified passing when recorded)
- `tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate::test_clean_policies_no_finding` (pytest node id, verified passing when recorded)
- `tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate::test_load_failure_skips_silently` (pytest node id, verified passing when recorded)
- `tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate::test_no_design_dir_noop` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 17 error(s), 4014 warning(s), 862 waived
- error-findings: AFFECT001@src/frob/gates/_policy_weakening_gate.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DUP001@src/frob/gates/_policy_weakening_gate.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3460, REL001@src/frob/__init__.py, SELFAUDIT001@src/frob/gates/_policy_weakening_gate.py, SELFAUDIT001@tests/unit/strata/test_strata_core_gil.py, SELFAUDIT001@tests/unit/verify/test_worker.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE001@tests/unit/test_policy_weakening_gate.py
