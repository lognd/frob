## Done report

(T-2318 reconciliation, 2026-08-18)

T-1238's ledger `state:` read `queued` on main while every deliverable it
tracks was already shipped. Reconciled here per T-2318's finding (no new
code -- ledger-only closure):

- Acceptance[1] (the `frob explore` first slice: un-deprecating
  map/outline/xref/docs-search) landed under commit T-1271 (bb7f37766),
  confirmed an ancestor of main directly (`git merge-base --is-ancestor
  bb7f37766 main`), with `src/frob/app/explore_runner.py` and
  `src/frob/_cli_parsers/_explore.py` present on main today. The prior
  Done report on this ticket cited commit 532799aca on a
  since-superseded branch -- that commit is NOT an ancestor of main;
  T-1271 is the real landed evidence and is the citation of record going
  forward.
- Acceptance[2] (the regrouping design doc) is satisfied:
  `docs/design/cli-regrouping.md` exists on main.
- Acceptance[0] (help-surface rework across every other verb group) was
  explicitly deferred, per the epic's own directive, to five child
  tickets: T-1567 (quality group), T-1568 (design group), T-1569 (ops
  group), T-1570 (ticket/debt/deprecated naming), T-1571 (help-surface
  rework). All five read `state: done` on main (verified via `frob
  ticket show` immediately before this closure).

No code changed by this ticket -- `tickets/T-1238/**` only.

### Evidence
Acceptance[1]: the same 5 node ids already bound, re-verified collectible
against this worktree's fresh natives build:
- tests/unit/test_app_runners.py::TestExploreRunner::test_map_subcommand_delegates_to_map_runner
- tests/unit/test_app_runners.py::TestExploreRunner::test_outline_subcommand_delegates_to_outline_runner
- tests/unit/test_app_runners.py::TestExploreRunner::test_xref_subcommand_missing_symbol_exits_1
- tests/unit/test_app_runners.py::TestExploreRunner::test_docs_search_subcommand_missing_path_exits_1
- tests/unit/test_app_runners.py::TestExploreRunner::test_unknown_subcommand_exits_1

Acceptance[0]/[2]: docs-only/deferred-to-children closure, no pytest
surface of its own -- per playbook section 5's docs-only precedent,
recorded against the existing CLI-dispatch integration test:
tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches

### Changed
```
 tickets/T-1238/ticket.md | 170 ++++++++++++++++++-----------------------------
 tickets/T-2318/ticket.md |   2 +-
 2 files changed, 64 insertions(+), 108 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners.py::TestExploreRunner::test_map_subcommand_delegates_to_map_runner` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_outline_subcommand_delegates_to_outline_runner` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_xref_subcommand_missing_symbol_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_docs_search_subcommand_missing_path_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_unknown_subcommand_exits_1` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_leases.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT002@src/frob/verify/_drain.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2318/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_leases.py, TICK004@tickets.md, WIRE003@docs/modules/cli.md
