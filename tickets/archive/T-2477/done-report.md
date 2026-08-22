## Done report

Verified each of the 5 filed (rule, file) identities directly, per the
coordinator's known false-positive pattern for this repo's sweep
mechanism (a stale baseline can report pre-existing findings as new;
one measured case had 5 of 6 "new" identities pre-existing while the
attribution engine correctly said UNATTRIBUTED and the sweep filed them
anyway).

Ran `ruff check --select E501,F401` directly against all 5 named files
at main's current tip: All checks passed -- zero E501/F401 violations
in any of the 5 files right now. This matches the ticket's own body,
which already discloses "An independent re-measurement found 0 actual
finding(s) across those 5 identit(ies)" and reports every identity as
UNATTRIBUTED (no batch commit's touched symbols reach any of them).

Conclusion: this is a stale-baseline false positive, not a genuine
regression from T-1135. No code change made -- there is nothing to fix.
Per the ticket's own closing instruction ("if they are pre-existing
residue the rolling baseline simply had not recorded yet -- close this
ticket with that finding stated explicitly"), closing with this
disclosure rather than manufacturing 5 unnecessary edits.

Scope note: T-2477's declared scope included
src/frob/app/ticket_runner/_query.py, which collided with T-2492's live
in-progress lease; removed it from scope before starting since no edit
to any of the 5 files was needed to resolve this ticket.

### Changed
```
 tickets/T-2477/ticket.md | 14 ++++++++++++--
 1 file changed, 12 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2477/src/frob/testing/_collect_kotlin.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md


frob:waive BUG002 reason="stale-baseline false positive, not a real defect -- all 5 filed (rule, file) identities are already 0 findings at main's current tip (ruff --select E501,F401 passes clean on all 5 files) and the ticket's own attribution audit reports every identity as UNATTRIBUTED; there is no code defect here to reproduce a fix for, only a rolling-baseline correction, per this ticket's own closing instruction"
