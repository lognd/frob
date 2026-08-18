## Done report

Premise no longer holds: verified `design/frob.strata`'s `testsuite` node
already declares `may "exec" via ... "tests/test_lang_conformance_gate.py"
...` (line 1399 of the current file) -- landed as part of T-2482 ("Declare
fs.read/fs.write/exec for T-2467's waive-audit module+tests (SELFAUDIT001
SYS100)", commit c46d3f156cd528098a4f7252ccd6e75d296f3a31, landed
2026-08-18 08:02 -04:00), which folded this file's exec sites into a
broader declaration alongside many other test files.

Measured: `frob check --only sys --ticket T-2490` on a worktree merged
current against main -- zero SYS100 findings anywhere in the output (`grep
-c SYS100` on the full check output: 0). The two errors that DO fire
(`gate:SELFAUDIT` SELFAUDIT001, testsuite's exec/fs.write via-list counts
exceeding `docs/design/registry/capability-via-ratchet.lock.json`'s
committed ceiling by 2 and 1 sites respectively) are a pre-existing,
repo-wide ratchet-ceiling condition unrelated to this ticket's own file
(the ceiling text names no specific file) and out of T-2490's declared
scope (`design/frob.strata` only, not the registry lock file) -- not
something this ticket's own plan asked to fix.

No code change made: `design/frob.strata` was not touched, since the
grant it asked for already exists on main. Closing as a clean negative
per playbook section 8 ("report only measured numbers... a clean negative
is a valuable result").

### Changed
```
 tickets/T-2490/ticket.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md


frob:no-behavior-change reason="premise already resolved on main by T-2482 before this ticket started; design/frob.strata already declares exec via tests/test_lang_conformance_gate.py, zero SYS100 findings measured, no code change made"
