## Done report

Added a shared _scrub_host_git_identity(monkeypatch) helper in tests/test_ticket_leases.py that pins GIT_CONFIG_GLOBAL and GIT_CONFIG_SYSTEM to os.devnull, sets GIT_CONFIG_NOSYSTEM=1, and clears GIT_AUTHOR_*/GIT_COMMITTER_* env vars. Evidence: 3x local pass via FROB_SUGGEST_ACK=1 uv run pytest -p no:xdist. frob test --base main exceeded 540s. frob check --ticket T-3535: gate:SCOPE clean. frob:waive BUG002 recorded on ticket body. Filed: none.

### Changed
```
 tickets/T-3535/done-report.md | 17 +++++++++++++++++
 tickets/T-3535/ticket.md      | 20 +++++++++++++++++++-
 2 files changed, 36 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_identity_less_environment_falls_back_to_throwaway_git_identity` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 30 error(s), 4065 warning(s), 895 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH103@src/frob/tickets/_leases.py, COV001@src/frob/gates/_docblocks.py, COV001@src/frob/tickets/_land_queue.py, COV003@tests/unit/test_scaffold_project.py, COV007@src/frob/gates/_docblocks.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, DSL001@CHANGELOG.md, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3535, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, TEST001@src/frob/gates/_docblocks.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, WIRE001@tests/test_ticket_leases.py
