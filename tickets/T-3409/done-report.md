## Done report

Replaced src/frob/stats/_agentic.py with src/frob/stats/_agentic_shared.py
in core's may "fs.read" via declaration in design/frob.strata --
T-3059's split moved the fs.read caller (_load_events) out of
_agentic.py into the new sibling module, and the design model never
followed. Closes the 6th and final SYS100 fs.read violation from the
T-3416/T-3409 pair (src/frob/stats/_agentic_shared.py:42).

Evidence: tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbolsCorpusWide::test_every_tracked_strata_file_symbol_count_matches_grammar_declared_count
(bound) parses the real design/frob.strata this change edits and passes
cleanly.

Manually re-verified (not bound as evidence -- see BUG002 waiver below):
tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
no longer reports the src/frob/stats/_agentic_shared.py:42 violation at
all after this fix (combined with T-3416, already landed). It now
reports 2 NEW, unrelated violations (tests/unit/test_arch_srp.py:616/:650,
testsuite node) that surfaced from a concurrent land on main after
T-3416 landed -- filed separately as T-3430, not this ticket's scope.
BUG002 waived (follow_up=T-3430) because the named test cannot show a
clean pass while that unrelated drift is outstanding.

Filed: T-3430 (SYS100: testsuite fs.read undeclared for
tests/unit/test_arch_srp.py)

Gates: frob check --ticket T-3409 clean aside from the waived BUG002
above.

### Changed
```
 tickets/T-3409/ticket.md | 17 +++++++++++++++--
 1 file changed, 15 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbolsCorpusWide::test_every_tracked_strata_file_symbol_count_matches_grammar_declared_count` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 10 error(s), 4184 warning(s), 857 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC006@tickets/T-3424/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
