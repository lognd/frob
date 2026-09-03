## Done report

refresh claims count after frob ticket evidence registered 9 test node ids

### Changed
```
 frob.lock                             |  20 +++-
 src/frob/check/__init__.py            |  68 +++++++++++++
 src/frob/gates/_fix_engine.py         |  19 ++++
 src/frob/gates/_fix_engine_shared.py  | 123 +++++++++++++++++++++--
 src/frob/gates/_waive.py              |   5 +
 tests/unit/test_fix_engine_journal.py | 178 ++++++++++++++++++++++++++++++++++
 tickets/T-3526/done-report.md         |  38 ++++++++
 tickets/T-3526/ticket.md              |  12 ++-
 tickets/T-3533/ticket.md    |  30 ++++++
 tickets/T-3534/ticket.md    |  29 ++++++
 10 files changed, 511 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournal::test_absent_manifest_is_not_abandoned` (pytest node id, verified passing when recorded)
- `tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournal::test_live_pid_manifest_is_not_abandoned` (pytest node id, verified passing when recorded)
- `tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournal::test_dead_pid_manifest_is_abandoned` (pytest node id, verified passing when recorded)
- `tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournal::test_malformed_journal_is_abandoned` (pytest node id, verified passing when recorded)
- `tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournal::test_no_journal_is_not_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournal::test_abandoned_journal_fails_check_loudly` (pytest node id, verified passing when recorded)
- `tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournal::test_completed_apply_tier_a_fixes_leaves_no_journal` (pytest node id, verified passing when recorded)
- `tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournal::test_run_check_is_unaffected_with_no_journal` (pytest node id, verified passing when recorded)
- `tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournalSigkillSubprocess::test_sigkilled_journal_writer_is_detected_and_refused` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 28 error(s), 4116 warning(s), 900 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH103@src/frob/tickets/_leases.py, COV001@src/frob/gates/_docblocks.py, COV001@src/frob/tickets/_land_queue.py, COV003@tests/unit/test_scaffold_project.py, COV007@src/frob/gates/_docblocks.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, DSL001@CHANGELOG.md, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@tests/unit/test_fix_engine_journal.py, TEST001@src/frob/gates/_docblocks.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
