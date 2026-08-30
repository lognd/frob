## Done report

Declared tests/unit/verify/test_bisect.py in the testsuite node's exec and fs.read via-lists (T-1691 added the file without declarations) and bumped the SYS111 ratchet ceilings (exec 230 to 234, fs.read 173 to 174) with measured reasons. TestRealGateGreen, test_sys_gate_zero_violations, and the eval-needle test all pass 3/3 in this worktree.

### Changed
```
 design/frob.strata                                    |  4 ++--
 docs/design/registry/capability-via-ratchet.lock.json | 12 ++++++------
 tickets/T-3484/ticket.md                              |  4 +++-
 tickets/T-3487/ticket.md                              |  2 ++
 4 files changed, 13 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 21 error(s), 4055 warning(s), 869 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@changelog.d/T-2691.md, DOC006@tickets/T-3489/ticket.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3484, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/app/ticket_runner/_land_cmd.py, WIRE002@src/frob/gates/_arch.py, WIRE002@src/frob/gates/_coverage_sites.py, WIRE002@src/frob/gates/_render_lint.py, WIRE002@tests/unit/test_new_ticket_scope_overlap_warning.py
