## Done report

Both CI trips fixed: (1) declared the 4 measured SYS111 ratchet growths (testsuite::exec 234->235, testsuite::fs.write 417->418, tickets_ledger::env 5->6, tickets_ledger::fs.write 21->22) in docs/design/registry/capability-via-ratchet.lock.json with reasons citing this ticket and CI run 33376126399; (2) fixed the DOC006 stale doc-pointer in docs/design/land-splice-test-then-impl.md.

STRUCTURAL HALF: root-caused why T-3324's land-time gate missed both; SYS111 findings carry no source-file path so substring-matching against touched files can never fire, and DOC006 was never inside T-3324's evaluated family. Filed T-3575 to extend the gate with a real per-family attribution strategy for each.

### Changed
```
 tickets/T-3574/done-report.md | 19 +++++++++++++++++++
 tickets/T-3574/ticket.md      |  7 +++++--
 2 files changed, 24 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 31 error(s), 4121 warning(s), 892 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3574, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, TICK006@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, call-top-callable@tests/conftest.py, invalid-argument-type@tests/conftest.py
