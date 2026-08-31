## Done report

refresh claims count after recording evidence-cmd

### Changed
```
 tickets/T-3076/ticket.md           | 13 +++++++++++++
 tickets/T-3511/done-report.md      | 30 ++++++++++++++++++++++++++++++
 tickets/T-3511/ticket.md           | 20 +++++++++++++++++---
 tickets/T-3539/ticket.md | 33 +++++++++++++++++++++++++++++++++
 tickets/T-3540/ticket.md | 38 ++++++++++++++++++++++++++++++++++++++
 5 files changed, 131 insertions(+), 3 deletions(-)
```

### Evidence
- `cmd:grep -n 'Re-measurement after the five primitive fixes' docs/design/windows-portability.md exit=0 sha256=a4d277d50889` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 29 error(s), 4061 warning(s), 894 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH103@src/frob/tickets/_leases.py, COV001@src/frob/gates/_docblocks.py, COV001@src/frob/tickets/_land_queue.py, COV003@tests/unit/test_scaffold_project.py, COV007@src/frob/gates/_docblocks.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, DSL001@CHANGELOG.md, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3511, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, TEST001@src/frob/gates/_docblocks.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
