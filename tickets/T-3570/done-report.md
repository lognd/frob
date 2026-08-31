## Done report

Added src/frob/logging/logger.py::_is_vet_hook_mode (a direct sys.argv scan, mirroring _resolve_stdout_level_override's own ordering-independent pattern) and wired it into _init(): in vet --hook mode, raises the stderr handler's threshold above WARNING to ERROR, extending T-3438's own 'machine-consumed stream must not leak' posture from the startup-nag prints to ordinary WARNING-level log records. Added tests/unit/test_logging_module.py::TestIsVetHookMode (4 tests: both-tokens/vet-only/hook-only/neither) to strengthen mutation coverage past the system test alone. Did not touch src/frob/process/_reap.py's prctl-failure WARNING (the literal leak source, ground-truthed against CI run 33370059331 as arm_parent_death_signal's darwin PR_SET_PDEATHSIG-unsupported warning) -- out of this ticket's originally declared scope; the general logger-layer fix closes the leak for every WARNING source regardless. Evidence: 3x local pass on all 5 node ids together, plus a full tests/system/test_cli_vet.py + tests/unit/test_main_entry.py regression run (43 tests, 0 failures). frob:waive BUG002: macOS-only leak source, cannot fail-then-pass on this Linux dev box. Filed: none.

### Changed
```
 tickets/T-3570/done-report.md | 18 ++++++++++++++++++
 tickets/T-3570/ticket.md      | 35 +++++++++++++++++++++++++++++++++--
 2 files changed, 51 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/system/test_cli_vet.py::TestHookMode::test_non_install_command_fast_exits_zero` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::TestIsVetHookMode::test_both_tokens_present_is_true` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::TestIsVetHookMode::test_vet_without_hook_is_false` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::TestIsVetHookMode::test_hook_without_vet_is_false` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::TestIsVetHookMode::test_neither_token_is_false` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 34 error(s), 4286 warning(s), 892 waived
- error-findings: ARCH001@src/frob/logging/logger.py, ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC006@docs/design/land-splice-test-then-impl.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, LANDPARITY002@src/frob/logging/logger.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3570, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, call-top-callable@tests/conftest.py, invalid-argument-type@tests/conftest.py
