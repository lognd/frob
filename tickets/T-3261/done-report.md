## Done report

Doc-only fix: added rule-catalog table rows for F401, I001, QUEUE001, TICK014, VERSION001, VMOD001 to docs/modules/gates.md so the file's own frob:enumerates directive resolves (DOCENUM001). The other 3 identities in this ticket (COV/REG/REL against T-3272/ticket.md, docs/design/registry/check-coverage.yaml, and strata-core/src/graph/vmodel.rs+grammar_core.rs) were already-stale: no live finding reproduces against them on this tree, and vmodel.rs itself no longer exists (split into strata-core/src/graph/vmodel/ by T-3260/T-3424).

### Changed
```
 docs/modules/gates.md    |  6 ++++++
 tickets/T-3261/ticket.md | 27 +++++++++++++++++++++++++--
 2 files changed, 31 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_claimed_member_with_doc_row_does_not_fire` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 9 error(s), 4281 warning(s), 856 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC006@tickets/T-3424/ticket.md, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
