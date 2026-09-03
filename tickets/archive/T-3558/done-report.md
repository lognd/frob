## Done report

tests/unit/test_fix_engine_journal.py's frob:waive WIRE001 on _write_journal_and_block had follow_up=T-3558 (auto-renumbered when this ticket was created from T-3534's re-point, since T-3534 was docs-only and could not carry it). Verified WIRE001 stays quiet on this file (frob check --only wire, no WIRE001 finding) and the referenced test (TestAbandonedAutofixJournalSigkillSubprocess::test_sigkilled_journal_writer_is_detected_and_refused) passes, confirming the function is genuinely wired via multiprocessing.Process's target= kwarg. Filed T-3576 (teach WIRE001's call-graph analyzer to resolve target= kwarg references) as the real fix for the underlying analyzer gap, and re-pointed the waiver's follow_up from T-3558 to T-3576, since T-3558 itself does no code change and cannot remain the live tracker once closed.

### Changed
```
 tickets/T-3558/done-report.md | 17 +++++++++++++++++
 tickets/T-3558/ticket.md      | 16 ++++++++++++++--
 2 files changed, 31 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournalSigkillSubprocess::test_sigkilled_journal_writer_is_detected_and_refused` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 31 error(s), 4093 warning(s), 892 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3558, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, WIRE002@tests/unit/test_fix_engine_journal.py, call-top-callable@tests/conftest.py, invalid-argument-type@tests/conftest.py
