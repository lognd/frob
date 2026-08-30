## Done report

Post-land sweep flagged DOC006 against docs/design/windows-portability.md (the T-3425 doc): its illustrative symref example, quoted as backtick path.py::symbol_name, was shaped exactly like a real file::symbol doc pointer, so DOC006 tried and failed to resolve path.py as a tracked file. Marked it explicitly illustrative with an inline frob:waive DOC006 comment, the same idiom already used elsewhere in this repo's docs (docs/audits/gates-quality.md, docs/audits/graph.md) for placeholder shapes that are not real tracked paths. No code changed. Verified with frob check --only docblocks: 0 findings remain against docs/design/windows-portability.md (the file's own line no longer appears in the gate:DOC output at all).

### Changed
```
 docs/design/windows-portability.md |  7 +++++--
 tickets/T-3432/ticket.md           | 19 +++++++++++++++++--
 2 files changed, 22 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006Waive::test_waive_suppresses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 11 error(s), 3970 warning(s), 855 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
