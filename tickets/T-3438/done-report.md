## Done report

Root cause: `frob vet --hook ...` goes through `_dispatch_default`, which
unconditionally calls `_print_startup_warnings` (stale binary/floor/
fingerprint advisories plus the T-1808 Claude-config-drift nag from
`frob.app.claude_runner.drift_warning`) before running the subcommand.
Hook mode is machine-consumed (a pre-tool-use hook parses stdout/exit
code), so any of those best-effort startup nags landing on stderr is a
contract break, not just this one drifted-config message -- the CI
failure happened to be the drift nag because that was this repo's actual
state, but the real defect is unconditional printing regardless of
`--hook`.

Fix: `_dispatch_default` now skips `_print_startup_warnings` specifically
for `vet ... --hook ...` invocations; every other subcommand, and `vet`
without `--hook`, is unaffected.

`frob test --base main` exceeded the 540s budget in this repro; relied on
targeted node-id runs instead per the dispatch brief.

Evidence:
- tests/unit/test_main_entry.py::TestVetHookSuppressesStartupWarnings
  (2 new tests: must-fire + must-stay-quiet)
- tests/system/test_cli_vet.py::TestHookMode::test_non_install_command_fast_exits_zero
- Full tests/unit/test_main_entry.py + tests/system/test_cli_vet.py: 43/43
  pass under -p no:xdist

### Changed
```
 tickets/T-3438/ticket.md | 6 +++++-
 1 file changed, 5 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestVetHookSuppressesStartupWarnings::test_vet_hook_suppresses_startup_warnings` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestVetHookSuppressesStartupWarnings::test_vet_without_hook_still_warns` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_vet.py::TestHookMode::test_non_install_command_fast_exits_zero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 14 error(s), 4053 warning(s), 855 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC007@tests/unit/test_main_entry.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, DRIFT002@tests/unit/test_main_entry.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3438, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
