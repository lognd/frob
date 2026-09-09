## Done report

Root cause: the macOS CI Test step (.github/workflows/ci.yml) invokes the
already-synced venv's own interpreter directly (`.venv/bin/python -m
pytest`, T-4274's fix, needed so `$!` captures pytest's own pid for the
stack-dump-on-hang mechanism) rather than through `uv run pytest`, unlike
ubuntu's step. `uv run` activates the target project's own environment
(prepending its bin dir onto PATH) before exec'ing the child; a direct
`.venv/bin/python` invocation never does. Without `.venv/bin` on PATH,
`shutil.which("ty")`/`shutil.which("mypy")` inside the test process return
None even though ty/mypy are this repo's own dev dependencies, present at
`.venv/bin/ty`/`.venv/bin/mypy` -- unreachable purely because of how the
CI step launches the interpreter.

Reproduced locally (platform-independent PATH-content defect, not
macOS-specific): `env -i PATH=/usr/bin:/bin .venv/bin/python -m pytest -q
tests/test_gates_suppress.py::TestSuppressionDialects::test_available_reflects_path_not_project_config`
fails with `dialects["ty"].available is False` before the fix.

Same root cause also drives the two `tests/test_ticket_merge_driver.py`
macOS failures (a real `git merge` spawning `uv run frob ticket
merge-driver ...` as the registered merge driver): reproduced with a
scratch git repo and `env -i PATH=<uv's own bin dir only> git merge ...`,
which fails with `error: Failed to spawn: frob` -- the identical PATH-
content shape, fixed by the same `.venv/bin` PATH export.

Fix: export `PATH="$PWD/.venv/bin:$PATH"` immediately before the
`.venv/bin/python -m pytest` invocation in the macOS Test step, so the
child test process (and any subprocess it spawns, including the merge
driver above) resolves this repo's own dev-dependency tools exactly as
`uv run` would. Kept the direct-interpreter invocation unchanged (does not
regress T-4274's pid-capture fix) -- only the PATH content changed.

Changed:
- .github/workflows/ci.yml (macOS Test step)
- tests/test_ci_workflow_matrix.py::TestMacosTestStepPutsVenvBinOnPath (new)

Evidence:
- tests/test_ci_workflow_matrix.py::TestMacosTestStepPutsVenvBinOnPath::test_macos_test_step_run_script_prepends_venv_bin_to_path
  -- designated BUG002 repro test, verified genuinely FAILED_AT_PARENT
  (commit be089d4a3, the test-only commit before the fix) and PASSES after
  the fix commit (007a9f205).
- Full `tests/test_ci_workflow_matrix.py` suite (20 tests) passes locally.
- Direct reproduction of the exact CI PATH shape confirmed the mechanism
  for the 7 macOS-only cluster-a failures (test_gates_suppress.py x3,
  test_gates_fix_engine.py x3, test_ticket_work_and_land_finish.py x1) and
  the 2 cluster-b merge-driver failures
  (test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_real_git_merge_auto_splices_both_sides_append,
  test_ticket_merge_driver.py::TestMergeDriverV2TicketFileViaRealGit::test_diverged_ticket_state_merges_cleanly_via_registered_driver)
  from CI run 34315257799, head 83a0cecd0.

Filed: none -- T-4369 (already landed separately) covers the distinct
mutation-evidence "uv run pytest against a throwaway repo" root cause
(cluster c); this ticket covers only the CI workflow's own PATH content.

Gates: `frob check --ticket T-4368 --only fmt --only prework --only
affect_drift --only drift --only land_parity` clean (0 errors). `frob
test --base main`: PASS.

Cannot verify on macOS directly (no macOS access this session); the
reproductions above simulate the exact PATH-content defect platform-
independently. State plainly: the CI-green confirmation for the 9 named
macOS failures (7 cluster-a + 2 cluster-b) must come from a macOS CI run.

### Changed
```
 .github/workflows/ci.yml         | 17 +++++++++++++++++
 tests/test_ci_workflow_matrix.py | 41 ++++++++++++++++++++++++++++++++++++++++
 tickets/T-4368/ticket.md         | 18 +++++++++++++++++-
 3 files changed, 75 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestMacosTestStepPutsVenvBinOnPath::test_macos_test_step_run_script_prepends_venv_bin_to_path` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 4781 warning(s), 969 waived
- error-findings: COV007@src/frob/tickets/_mutation_evidence.py, PRE001@tickets/T-4368, SUPPRESS001@tests/unit/test_dup_smt.py
