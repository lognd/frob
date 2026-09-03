## Done report

Added tests/test_check_runner.py to design/frob.strata's testsuite node
may "exec" via [...] list -- its _git_init fixture already calls
subprocess.run at lines 38/39/42/282/283, which SELFAUDIT001's full-tree
self-conformance scan (not diff-scoped, per _selfaudit_violations ->
check_self_conformance) flagged as unaccounted exec capability use since
the strata node was last synced.

That edit grows testsuite's exec via-list from 223 to 224 sites, tripping
the SYS111 ratchet ceiling in docs/design/registry/capability-via-ratchet.lock.json,
so bumped accepted_count to 224 with a reason in the same diff.

Verified via gate:SELFAUDIT rendered output: 2 errors before the fix
(testsuite ceiling trip + a pre-existing unrelated refactor node ceiling
trip), 1 error after (only the pre-existing refactor finding remains,
confirmed via git log to predate this ticket and unrelated to
design/frob.strata's testsuite node). tests/unit/gates/test_sys_selfaudit.py
plus tests/unit/strata/test_selfconform.py: 80 collected, 0 failed.

Filed T-3388 for the pre-existing refactor-node ratchet gap
(no "refactor::exec" entry in the lock file at all) rather than fixing it
here -- out of this ticket's scope.

Third data point for T-3324 (live-repo conformance checks rot as
unrelated work lands): T-3311 landed unrelated work, and its lease
blocked Series EO's diagnosis of this exact drift until the lease
cleared.

### Changed
```
 tickets/T-3386/done-report.md      | 43 +++++++++++++++++++++++++++++++++
 tickets/T-3386/ticket.md           | 28 ++++++++++++++++++++--
 tickets/T-3388/ticket.md | 49 ++++++++++++++++++++++++++++++++++++++
 3 files changed, 118 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_defaults_to_warn` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceCore::test_core_undeclared_interface_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 35 error(s), 4148 warning(s), 880 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/check_runner.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/app/ticket_runner/_verify.py, ARCH103@src/frob/refactor/_verify.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC003@docs/commands/sys.md, DOC011@docs/modules/tickets.md, DOCENUM001@docs/modules/gates.md, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
