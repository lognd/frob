## Done report

Root cause: a fresh `git worktree add` copies tracked files only, never
`.venv/` (gitignored), so a freshly-created `frob ticket work` worktree has
no venv until an agent runs `uv sync` by hand -- `ty` then fails "Cannot
resolve imported module" for every declared dep. `_build_natives_for_work`
already ran unconditionally at worktree warmup for native crates; this adds
`_sync_venv_for_work`, same best-effort posture, running BEFORE it (native
crates build into the venv `uv sync` populates) so a fresh worktree's first
`frob check --ticket` just works with no manual step.

Filed: none.

Gates: `frob check --ticket T-3320` clean of new findings -- remaining
errors are pre-existing repo-wide (DEPR006/WAIVE011 lock-producer
staleness, T-3410/T-3411 unrelated ticket findings, TICK004 rot warnings,
DRIFT001 in _rapid_sweep.py), none touching this ticket's scope. `frob
test --base main` pass (7 outcomes, exit=0); node-id pytest -p no:xdist on
the new test file: 4 passed, 0 failed.

### Changed
```
 tickets/T-3320/ticket.md | 14 +++++++++++++-
 1 file changed, 13 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_ticket_runner_venv_sync_t3320.py::TestSyncVenvForWork::test_runs_uv_sync_in_the_worktree` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_venv_sync_t3320.py::TestSyncVenvForWork::test_exec_disabled_degrades_to_a_warning_not_sys_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_venv_sync_t3320.py::TestSyncVenvForWork::test_nonzero_exit_degrades_to_a_warning_not_sys_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_venv_sync_t3320.py::TestSyncVenvForWork::test_runs_before_natives_build_in_the_work_flow` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 8 error(s), 4040 warning(s), 857 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
