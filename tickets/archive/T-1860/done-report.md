## Done report

Premise re-verified before landing (per coordinator instruction): the
stranded worktree's 19-line diff targeted docs/modules/tickets.md, which
has since been split (T-1780) into several subject-scoped files -- the
cross-ticket-leakage section this ticket was meant to update now lives in
docs/modules/tickets-landing.md, already this ticket's own declared scope
on main (a hint the split anticipated exactly this move). The stranded
branch's diff against CURRENT main showed thousands of unrelated lines
(the pre-split content reappearing as a "revert"), confirming a re-apply
via that branch would have been wrong, not just risky -- re-derived the
fix fresh against current main instead of touching the stranded branch at
all.

Added the T-1855 per-path reason-disclosure paragraph ("declared" vs
"implicit-cli-wiring") to docs/modules/tickets-landing.md's "Cross-ticket
leakage only refuses on an IN_PROGRESS sibling (T-1639)" section
(src/frob/tickets/_land.py::_check_cross_ticket_leakage's frob:doc
target), and dropped the frob:waive AFFECT001 T-1855 left on that
function now that the anchor is current. Verified clean:
`frob check --ticket T-1860 --only affect_drift --only drift` shows zero
AFFECT001 findings (all 3 remaining DRIFT errors are pre-existing and
unrelated -- rapid_sweep.py DRIFT001, vet.md DRIFT002).

Docs-only ticket, no new pytest surface -- evidence recorded per the
T-0167 precedent (playbook section 5): the CLI-dispatch integration test.

### Changed
```
 tickets/T-1860/ticket.md | 15 ++++++++++++++-
 1 file changed, 14 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/dev-friction/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/dev-friction/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/dev-friction/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
