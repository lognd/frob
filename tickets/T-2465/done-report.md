## Done report

Declared the genuine fs.read capability SELFAUDIT001/SYS100 flagged for
src/frob/release/_fragments.py (T-2445's own new module: changelog.d/*.md
fragment reads via Path.exists()/Path.read_text() at lines 169/294).

Verified before declaring (per the T-2457 false-positive lesson cited in
this ticket): read the two call sites directly -- both are genuine reads,
no writes -- so declaring fs.read is correct, not the "declare to silence
a phantom finding" pattern T-2457 fixed.

design/frob.strata: added "src/frob/release/_fragments.py" to the core
node's existing may "fs.read" via-list (line ~789), the same list that
already covers src/frob/release/__init__.py.

docs/design/registry/capability-via-ratchet.lock.json: core::fs.read
ceiling bumped 32 -> 33 (this new site), reason recorded, same posture as
the T-2453/T-2407 precedent bumps in this file.

New regression test (tests/system/test_frob_self_model.py):
test_fragments_module_fs_read_is_declared_not_selfaudit001 runs the real
frob.graph.build_graph + frob.gates.sys_gate path against this repo's own
live design/frob.strata (same real-path pattern as the existing
test_sys_gate_zero_violations in this class) and asserts no violation
mentions _fragments.py -- narrower than the existing zero-violations test
so this regression cannot be masked by (or conflated with) the other,
unrelated, already-present SYS101/GATERULE001 findings that test also
currently trips on.

Verified: `frob check --only sys` before this change showed 2
SELFAUDIT001/SYS100 findings at src/frob/release/_fragments.py:169,294;
after, zero. `frob check --ticket T-2465` shows zero SELFAUDIT001/SYS111
findings referencing _fragments.py, frob.strata, or the ratchet lock --
the 4 remaining SELFAUDIT001 findings (SYS101 fs.write on
checker/fleet/deploy/vet) are pre-existing and unrelated (verified: none
mention _fragments.py or this ticket's scope files).

Gates: scoped `frob check --ticket T-2465` -- gate:SCOPE clean, no new
SCOPE001/COV001/DRIFT findings on any file this ticket touched.

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_fragments_module_fs_read_is_declared_not_selfaudit001`

### Changed
```
 tickets/T-2465/ticket.md | 20 +++++++++++++++++++-
 1 file changed, 19 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_fragments_module_fs_read_is_declared_not_selfaudit001` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2462/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2462/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2462/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2462/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2462/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2465, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py
