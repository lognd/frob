## Done report

Changed: docs/modules/tickets.md (T-draft-ad5e921b -> T-3360). Evidence: frob check --only docstatus shows zero DOC011 findings against this file post-fix. Gates: DOC011 no longer fires; the only remaining --only docstatus error (WAIVE011) is unrelated pre-existing repo-wide drift tracked T-3279.

### Changed
```
 docs/modules/tickets.md  |  2 +-
 tickets/T-3414/ticket.md | 17 +++++++++++++++--
 2 files changed, 16 insertions(+), 3 deletions(-)
```

### Evidence
- `cmd:bash -c 'uv run frob check --only docstatus 2>&1 | tee /tmp/doc011check.log; ! grep -q DOC011 /tmp/doc011check.log' exit=0 sha256=6f613c5c730e` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 15 error(s), 4060 warning(s), 857 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-1382/ticket.md, DOC006@tickets/T-3410/ticket.md, DOC006@tickets/T-3411/ticket.md, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, SYS003@src/frob/gates/__init__.py, SYS003@src/frob/tickets/_scope_coverage.py, SYS003@tests/unit/test_nodeid.py, TEST001@src/frob/lang/__init__.py, TEST001@src/frob/lang/_extract.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/nodeid.py
