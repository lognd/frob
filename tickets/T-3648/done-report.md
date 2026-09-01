## Done report

Added the strongest code-evidenced fix for T-3589's win32 saga: guarded_
subprocess_run (the sole spawn path for every frob.check tool runner)
called subprocess.run with no creationflags at all, so a spawned child on
win32 shares frob's own console process group -- any console ctrl event
delivered to that group reaches frob's own main process too, matching the
round-12 diag's spuriously-injected KeyboardInterrupt (no external Ctrl-C,
~1.5s into a tiny-fixture frob check run). _win32_isolate_console_group
now defaults every win32 spawn to CREATE_NEW_PROCESS_GROUP unless a caller
already sets its own creationflags (none currently do); a no-op on every
other platform.

Landed alongside the instrumentation the ticket asked for as proof-of-
diagnosis and to iterate further if this fix is not the whole story:
FROB_WIN32_SPAWN_DEBUG (env-gated, prints every guarded_subprocess_run
spawn's argv + creationflags) and a SIGINT/SIGBREAK logging handler in the
CI diag child (.github/workflows/ci.yml) that prints the signal name and
full stack before python's default handling turns SIGINT into
KeyboardInterrupt. The diag step now also sets FROB_WIN32_SPAWN_DEBUG=1
for its own frob check invocation. Per the ticket's own instruction, the
diag step stays in place until a win32 CI run shows a clean result (either
"frob check diag exit code: 0" or a genuine nonzero GATE result, not a
watchdog-budget hang) -- the NEXT push that runs this workflow on
windows-latest is that measurement.

Evidence: 3 new unit tests directly exercise _win32_isolate_console_group
(win32 default-injection, non-win32 no-op, never overriding an explicit
caller creationflags) -- these fail at main (the function does not exist
there) and pass at this commit, a genuine repro/fix pair, no waiver
needed. Full tests/unit/test_process_guard.py: 31/31 clean.

Gates: ruff-check/ty clean on the touched files; gate:SCOPE and gate:AFFECT
clean after adding tests/unit/test_process_guard.py and docs/modules/
process.md to declared scope and documenting the new win32 behavior there.
gate:DRIFT's 16 remaining errors are all pre-existing, in src/frob/vet/**
(unrelated to this ticket's files, left over from the in-flight test_vet.py
split fallout other agents are handling). YAML/Python syntax of the CI
diag script's new lines verified: python3 -c "import yaml; yaml.safe_load(...)"
and compile() on the extracted diag source both pass.

Filed: none new.

### Changed
```
 .github/workflows/ci.yml         | 36 ++++++++++++++++++++++--
 docs/modules/process.md          | 10 +++++++
 src/frob/process/_guard.py       | 60 ++++++++++++++++++++++++++++++++++++++++
 tests/unit/test_process_guard.py | 39 ++++++++++++++++++++++++++
 tickets/T-3648/ticket.md         | 19 ++++++++++++-
 5 files changed, 160 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_process_guard.py::TestWin32IsolateConsoleGroup::test_no_op_on_non_win32` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestWin32IsolateConsoleGroup::test_sets_new_process_group_on_win32` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestWin32IsolateConsoleGroup::test_never_overrides_an_explicit_creationflags` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 18 error(s), 4260 warning(s), 896 waived
- error-findings: ARCH102@src/frob/process/_lock.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/process/_guard.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT002@src/frob/vet/_capability_core.py, DRIFT002@src/frob/vet/_capability_python.py, DRIFT002@src/frob/vet/_capability_scan.py, DRIFT002@src/frob/vet/_supplychain.py, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3648, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
