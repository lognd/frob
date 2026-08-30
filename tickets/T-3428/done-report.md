## Done report

Root cause: T-3245 changed `_file_regression_ticket`'s body (wrapped the
`new_ticket(...)` call in `allocator_lock(root), ledger_lock(root)` to
close a cross-process duplicate-filing race, T-3236/T-3237 etc.) without
updating docs/modules/tickets-verify-sweep.md's Symbolic attribution
(T-1690) section, whose acked narrative describes this function's
filing/attribution/dispose behavior but was silent on the locking fix.
The acked body digest went stale (DRIFT001).

Fix (not a blanket re-ack): re-read the whole "Symbolic attribution"
section against the CURRENT `_file_regression_ticket` body -- the
attribution/dispose narrative (T-1690/T-2208) is still accurate as
written. Added a new paragraph documenting T-3245's fix specifically
(the race, the two locks, why the SAME reentrant flocks close it), then
re-acked with a reason stating exactly what was re-verified and what was
added.

Evidence:
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket: 16/16 pass
  under -p no:xdist
- `frob check --only drift`: DRIFT001 on
  src/frob/app/ticket_runner/_rapid_sweep.py is gone (zero hits on that
  file in the drift/coverage output)

### Changed
```
 tickets/T-3428/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_commit_failure_skips_auto_dispose_and_returns_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 7 error(s), 4154 warning(s), 856 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
