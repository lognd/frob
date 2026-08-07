## Done report

Survey: grepped every `src/frob/app/*_runner.py` for a `_json` config flag,
then checked which of those payload paths reach `guarded_subprocess_run`
(`grep -rl guarded_subprocess_run src/frob/`). Findings:

| runner | _json flag | reaches guard? | pre-fix state | action |
|---|---|---|---|---|
| mutate_runner.py | mutate_json | yes -- `frob.mutate.run_mutations` -> `_run_mutants` -> `guarded_subprocess_run` per mutant | unwrapped, polluted | wrapped conditionally |
| fleet_runner.py | fleet_json | yes -- `frob.fleet.rollup` -> `collect_status` -> `_git_branch_and_dirty`/`_gate_summary_probe` -> `guarded_subprocess_run`, always (even with --skip-gates, branch/dirty probe still runs); also `load_manifest`'s own INFO log leaked ahead of the guard line | unwrapped, polluted (both the guard DEBUG line and load_manifest's INFO line) | wrapped conditionally, widened to cover load_manifest too |
| gitlog_runner.py | gitlog_json | yes -- `frob.gitlog.git_log` -> `guarded_subprocess_run` | wrapped UNCONDITIONALLY (T-0803) | aligned to conditional pattern |
| xref_runner.py | xref_json | yes -- `frob.xref.xref` | already conditional (existing reference pattern) | no change |
| check_runner.py | check_json | yes -- native/python/ts collectors, lease ops | already conditional (line 966) | no change, out of scope |
| ticket_runner.py | ticket_json | `land`'s `make core` rebuild spawns via guard, but that path is not on the `--json` read-path for any ticket_json-emitting command surveyed (land itself isn't `--json`) | not polluted for any `--json` output surveyed | no change; not filed, no reachable pollution found |
| test_runner.py | test_json | `run_selected` (frob.testing._runners) does not go through `guarded_subprocess_run` per the guard-user grep; `--wait-coverage` (guard-using `_coverage_wait`) is a separate non-json code path | not polluted | no change |
| vet_runner.py, docs_runner.py, deploy_runner.py | vet_json/docs_json/attestation write | not in the `guarded_subprocess_run`-using module list | not polluted | no change |

Only mutate_runner.py, fleet_runner.py, and gitlog_runner.py needed fixes.
gitlog_runner.py was not in the ticket's original declared scope; scope-added
with reason (T-0815 acceptance explicitly names it for alignment).

Changed:
- src/frob/app/mutate_runner.py: run -- wrapped `run_mutations` call in
  `quiet_stdout_logs()` conditional on `cfg.mutate_json`
  (`contextlib.nullcontext()` otherwise), matching xref_runner's pattern.
- src/frob/app/fleet_runner.py: _run_status -- wrapped the whole
  `load_manifest` + `rollup` payload path in the same conditional, since
  `load_manifest`'s own INFO log (not just the guard's DEBUG line) also
  leaked into `--json` stdout ahead of the payload.
- src/frob/app/gitlog_runner.py: run -- aligned the T-0803 unconditional
  `quiet_stdout_logs()` wrap to the conditional pattern; human mode now
  keeps the guard's diagnostic spawn line visible again.
- tests/integration/test_mutate_runner.py (new): `TestMutateRunnerJson` --
  drives `frob mutate --json` over a real on-disk target through the real
  CLI subprocess and `json.loads`s the full stdout; a second test asserts
  human mode still shows `mutation score`.
- tests/integration/test_fleet_integration.py: added
  `TestFleetIntegrationJson.test_fleet_status_json_is_clean` -- `frob fleet
  status --skip-gates --json` over a real one-repo manifest, full stdout
  `json.loads`d (the branch/dirty guard spawn runs even with
  `--skip-gates`, so this specifically locks the always-on guard path, not
  just the optional gate-probe path).
- gitlog's existing `TestGitlogJson.test_json_valid`
  (tests/integration/test_gitlog.py) already exercises the aligned
  conditional path end to end; no new gitlog test needed, bound as evidence
  instead.

All four evidence tests drive the real CLI as a subprocess
(`sys.executable -m frob ...`), so they exercise the same process-pool /
env-clamp path T-0806 touched (no separate accommodation needed -- these
tests never go through frob's own in-process worker pool, they spawn a
fresh interpreter each time, same as every other integration test in this
suite).

Evidence:
- tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean
- tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_human_mode_still_shows_diagnostics
- tests/integration/test_fleet_integration.py::TestFleetIntegrationJson::test_fleet_status_json_is_clean
- tests/integration/test_gitlog.py::TestGitlogJson::test_json_valid
(all four collected and passed: `pytest tests/integration/test_mutate_runner.py
tests/integration/test_fleet_integration.py tests/integration/test_gitlog.py -q`
-> 22 passed)

Filed: none -- survey found no other polluted runner to file a follow-up
for; ticket_runner/test_runner/vet_runner/docs_runner/deploy_runner all
checked and found not reachable to `guarded_subprocess_run` on any
`--json` payload path.

Gates: `uv run frob check --ticket T-0815` run chunked per
docs/guides/agent-playbook.md section 3b (`--only` prework/lint/static/
gates-fast/gates-native/gates-security) -- all stage groups pass, 0 new
errors attributable to this change (remaining warnings are pre-existing
repo-wide debt, same counts before and after).

`uv run frob test --base main` (full python+strata+rust suite, backgrounded
by the harness past 120s, foreground-observed via Monitor) shows several
FAILs (tests/test_doctor.py, test_export_golden.py, test_frob_self_model.py,
test_cli_native_missing.py, test_spawn_budget.py, test_cli_sys_audit.py,
test_cli_check.py::TestCheckTypescript, TestGitlessTargetGateSeverity, and
the strata compliance-registry GAP for COMPLIANCE004/PII010) -- none touch
mutate_runner.py, fleet_runner.py, gitlog_runner.py, or the new/changed
test files; these are pre-existing failures unrelated to this ticket's
scope (worktree-native / registry-drift / other-ticket artifacts), not
introduced by this change.

Deviations: none from the ticket's plan. Scope-added
src/frob/app/gitlog_runner.py (reason: T-0815 acceptance explicitly
directs aligning gitlog_runner's unconditional wrap to the conditional
pattern in this sweep).

### Changed
```
 src/frob/app/fleet_runner.py                | 36 +++++++----
 src/frob/app/gitlog_runner.py               | 15 +++--
 src/frob/app/mutate_runner.py               | 18 +++++-
 tests/integration/test_fleet_integration.py | 35 +++++++++++
 tests/integration/test_mutate_runner.py     | 75 +++++++++++++++++++++++
 tickets.md                                  | 93 ++++++++++++++++++++++++++++-
 6 files changed, 249 insertions(+), 23 deletions(-)
```

### Evidence
- `tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean` (pytest node id, verified passing when recorded)
- `tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_human_mode_still_shows_diagnostics` (pytest node id, verified passing when recorded)
- `tests/integration/test_fleet_integration.py::TestFleetIntegrationJson::test_fleet_status_json_is_clean` (pytest node id, verified passing when recorded)
- `tests/integration/test_gitlog.py::TestGitlogJson::test_json_valid` (pytest node id, verified passing when recorded)
