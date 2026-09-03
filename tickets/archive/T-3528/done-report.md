## Done report

T-3500 already added darwin dispatch across every real scoped code path; only the doc was stale (see frob:waive BUG002 in body)

### Changed
```
 tickets/T-3528/done-report.md | 17 +++++++++++++++++
 tickets/T-3528/ticket.md      | 18 ++++++++++++++++--
 2 files changed, 33 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_finds_a_process_cwd_into_the_path` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_recycled_pid_with_mismatched_starttime_is_treated_stale` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 33 error(s), 4107 warning(s), 891 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC006@docs/design/land-splice-test-then-impl.md, DOC006@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3528, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, call-top-callable@tests/conftest.py, invalid-argument-type@tests/conftest.py
