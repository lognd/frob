## Done report

tests/unit/test_check_admission.py's `_init_repo`/worktree-fixture helpers
(added by T-3256/T-3287) call `subprocess.run` for real git init/worktree
commands, ten exec sites never declared in `design/frob.strata`'s testsuite
node `may "exec" via [...]` list -- caught by test_sys_gate_zero_violations
(SELFAUDIT001, SYS100 family), first measured on GitHub Actions run
33282540898.

Fix: added tests/unit/test_check_admission.py to testsuite's exec via-list
in design/frob.strata (it was already present in the fs.write via-list, so
only exec was missing). Added a narrow, non-maskable regression test
(test_check_admission_exec_sites_are_declared_not_selfaudit001) in
tests/system/test_frob_self_model.py, following the exact precedent of the
two existing tests in that class (test_fragments_module_fs_read_is_declared_
not_selfaudit001, test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_
selfaudit001) -- filters sys_gate violations to only this file's, so it is
not masked by T-3447's separate, unrelated SYS111 ratchet findings.

Verified: the new narrow test passes; the full tests/unit/test_check_
admission.py suite (31 tests) still passes unchanged. The full test_sys_gate_
zero_violations remains red in THIS worktree only because T-3447's SYS111
ratchet fix (a sibling, unlanded ticket) is not yet merged into this branch
-- confirmed by diffing the violation list before/after this fix: SELFAUDIT001
findings dropped from 15 to 5, and all 5 remaining are SYS111 ratchet
messages naming core/testsuite capability-ratchet ceilings, none mentioning
test_check_admission.py.

Note for T-3447: declaring this file's exec sites bumped testsuite::exec's
measured site count from 225 to 226 (one more than the count T-3447's own
ratchet-lock bump assumed) -- T-3447 will need to re-measure and bump to
226, not 225, after merging this land.

### Changed
```
 tickets/T-3450/ticket.md | 22 ++++++++++++++++++++--
 1 file changed, 20 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_check_admission_exec_sites_are_declared_not_selfaudit001` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 15 error(s), 4195 warning(s), 856 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC007@tests/unit/test_main_entry.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, DRIFT002@tests/unit/test_main_entry.py, DUP001@tests/system/test_frob_self_model.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3450, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
