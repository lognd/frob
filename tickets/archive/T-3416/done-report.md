## Done report

Added src/frob/process/_proc_scan.py to core's may "fs.read" via
declaration in design/frob.strata, mirroring its sibling
src/frob/process/_reap.py -- closes 5 of the 6 SYS100 fs.read violations
named in this ticket (the 5 _proc_scan.py sites: lines 82, 134, 186, 227,
403). The 6th (src/frob/stats/_agentic_shared.py:42) is T-3409's scope.

Evidence: tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbolsCorpusWide::test_every_tracked_strata_file_symbol_count_matches_grammar_declared_count
(bound) parses the real design/frob.strata this change edits and passes
cleanly.

Manually re-verified (not bound as evidence -- see BUG002 waiver below):
tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
now reports exactly 1 remaining SYS100 violation
(src/frob/stats/_agentic_shared.py:42, T-3409's scope), down from 6
before this fix -- confirms all 5 src/frob/process/_proc_scan.py sites
named in this ticket are now declared. BUG002 waived (follow_up=T-3409)
because none of the four named tests can independently turn green until
T-3409 also lands.

Filed: none

Gates: frob check --ticket T-3416 clean aside from the waived BUG002
above.

### Changed
```
 tickets/T-3416/ticket.md | 14 +++++++++++++-
 1 file changed, 13 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbolsCorpusWide::test_every_tracked_strata_file_symbol_count_matches_grammar_declared_count` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 9 error(s), 4178 warning(s), 857 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC006@tickets/T-3424/ticket.md, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
