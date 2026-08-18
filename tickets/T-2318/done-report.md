## Done report

Verified the premise directly before acting (playbook: verify, don't
invent work):
- `git merge-base --is-ancestor bb7f37766 main` -> true (T-1271's landed
  commit is an ancestor of main).
- `src/frob/app/explore_runner.py` and `src/frob/_cli_parsers/_explore.py`
  present on main.
- `frob ticket show T-1567/T-1568/T-1569/T-1570/T-1571` -> all `state:
  done` on main.
- `docs/design/cli-regrouping.md` present on main (acceptance[2]).

All confirmed: T-1238's ledger `state:` was stale bookkeeping, not a real
gap. Fixed via `frob ticket close T-1238` (see T-1238's own Done report
for the closure rationale and evidence citations, now updated to cite
T-1271/bb7f37766 as the real acceptance[1] evidence in place of the
superseded 532799aca commit, plus T-1567..T-1571 as acceptance[0]'s
child-ticket closure and docs/design/cli-regrouping.md for acceptance[2]).

No code changed -- `tickets/T-1238/**` only, per this ticket's own scope.

### Evidence
Docs-only ledger reconciliation, no pytest surface of its own -- recorded
against the existing CLI-dispatch integration test per playbook section 5's
docs-only precedent:
tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches

Filed: none (premise confirmed exactly as described, no further gaps found)

### Changed
```
 tickets/T-1238/done-report.md | 122 +++++++++++-------------------
 tickets/T-1238/ticket.md      | 170 ++++++++++++++++--------------------------
 tickets/T-2318/ticket.md      |   6 +-
 3 files changed, 112 insertions(+), 186 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_leases.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT002@src/frob/verify/_drain.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2318/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_leases.py, TICK004@tickets.md, WIRE003@docs/modules/cli.md
