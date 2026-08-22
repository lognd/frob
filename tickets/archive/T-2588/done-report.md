## Done report

Root-caused and fixed both defects the ticket described, in
`src/frob/app/cycle_runner.py`.

Defect 1 (false clean) confirmed: `_build_graph`/`_process_path` resolved
node identity AND absolute-import edges relative to whatever path the
caller passed as `root` -- never against the project's own declared
import root. `resolve_local_import`'s python branch (`frob.lang._nodes`)
requires `pyproject.toml` to sit directly under the `root` it is given
to find any `[tool.setuptools] packages.find.where` src-layout roots;
`src/frob` has no `pyproject.toml`, so every absolute `import frob.x`
silently failed to resolve and contributed no edge -- a graph with no
edges reports no cycles.

Fix: added `_resolve_project_root` (walks up from the given path to the
nearest `pyproject.toml`, falling back to the git repo root) and anchored
BOTH node identity and edge resolution on that resolved root, regardless
of which subdirectory the CLI was pointed at. `_build_graph` now returns
`None` (never an empty/clean graph) when no project root can be resolved,
and `run()` treats that as a hard refusal, exit 2, with an explicit
"imports were NOT measured, this is not a clean report" message --
distinguishing UNRESOLVED from CLEAN in the output text, not just
internally.

Defect 2 (exit 0 on findings) fixed: `run()` now calls `sys.exit(1)`
after reporting any cycle.

Positive controls, measured directly against this repo's own tree
(commit range 5ddd8aae4^..04cc9fb97):

- `frob cycle src/frob`, `frob cycle src`, `frob cycle .` all report the
  SAME 7 cycles (including the 160-node SCC) and all exit 1.
- A synthetic acyclic `src/`-layout fixture reports "no cycles found"
  from all three path shapes, exit 0.
- A planted 2-node cycle in the same fixture is detected from all three
  path shapes, exit 1.
- An unresolvable path (no pyproject.toml, no git repo) errors with exit
  2 and an explicit "did not measure" message, from both the CLI and
  `_build_graph` directly.
- `tests/unit/test_capability_and_deploy_cycle_regression.py::
  TestPlantedCycleStillDetected` (detector-level positive control) still
  passes unchanged.

Collateral repair: `tests/unit/test_app_runners_batch5.py::
TestCycleRunner`'s fixtures used a bare `tmp_path` with no
`pyproject.toml`/git repo, which the fix now correctly refuses as
unresolved instead of silently treating as an acyclic project. Added a
`_make_project_root` helper stamping a minimal `pyproject.toml` into each
fixture, and updated `test_cycle_found_with_suggest` to assert the new
nonzero exit on a real cycle (it previously asserted nothing about exit
code and would have masked a regression here).

`docs/modules/app.md#runners`' `cycle_runner.run` bullet needed an
update for AFFECT001 (the runner's contract changed: root resolution,
distinct refusal exit code, findings now exit nonzero) but that file
sits under T-2582's live cross-worktree scope lease for the duration of
this ticket (`ScopeLeaseConflict` on `frob ticket scope --add`) -- waived
AFFECT001 in-line with a reason citing the lease and the doc text this
still owes; the ticket text should be applied once that lease clears.

Filed: none new -- both defects were already ticketed (T-2588 itself);
the doc-update-once-lease-clears note above is tracked via the waiver
reason, not a separate ticket, since it is a direct completion of this
ticket's own scope rather than new work.

Gates: `frob check --only docanchor --only drift --only render_lint
--only prework --only scope --only tickets --only affect_drift --only
suppress --ticket T-2588` -- gate:AFFECT, gate:SCOPE both PASS (0
errors) after the waiver and scope-add; the remaining FAILs
(gate:DOC/DRIFT/RENDER/TICK) are pre-existing repo-wide debt unrelated
to this ticket (grepped the full findings list for cycle_runner/
test_cycle_runner -- zero hits).

### Changed
```
 src/frob/app/cycle_runner.py                    |  90 ++++++++++++--
 tests/unit/test_app_runners_batch5.py           |  20 ++-
 tests/unit/test_cycle_runner_root_resolution.py | 155 ++++++++++++++++++++++++
 tickets/T-2588/ticket.md                        |  26 +++-
 4 files changed, 276 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_naive_relative_resolution_would_have_missed_this` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_all_path_shapes_agree_on_a_real_cycle` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_all_path_shapes_stay_clean_on_an_acyclic_tree` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_unresolvable_path_refuses_instead_of_reporting_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_run_exits_nonzero_on_a_found_cycle` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_run_exits_zero_on_a_clean_tree` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_run_exits_nonzero_error_on_unresolvable_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestCycleRunner::test_cycle_found_with_suggest` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC006@tickets/T-2585/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2588/src/frob/app/cycle_runner.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2588/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2588/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
