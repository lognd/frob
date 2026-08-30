## Done report

strata-core's V-model additions (T-3044/T-3260) added new construct keywords (architecture, configuration, entity) and clause keywords (architecture, code_ref, entity, obligation, runnable) to the parser but editors/vscode-strata/syntaxes/strata.tmLanguage.json's declaration-keywords and clause-keywords regex patterns were never updated, so the parser<->grammar drift-lock tests failed both locally and on CI (a real defect, not an environment artifact). Added the missing keywords alphabetically into the existing regex alternations. No JetBrains-specific grammar mirror exists to update: editors/jetbrains/README.md documents that JetBrains IDEs point the TextMate Bundles plugin directly at editors/vscode-strata/ (same file, zero duplication), so there is nothing further to sync.

### Changed
```
 editors/vscode-strata/syntaxes/strata.tmLanguage.json | 4 ++--
 tickets/T-3445/ticket.md                              | 5 ++++-
 2 files changed, 6 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally` (pytest node id, verified passing when recorded)
- `tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 11 error(s), 3983 warning(s), 856 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
