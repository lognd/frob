---
id: T-2329
title: design/frob.strata missing exec/fs.read grant for test_lang_strata.py (T-2194
  residue, dropped by T-2328's land defect)
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
evidence_scope:
- tests/unit/test_lang_strata.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbolsCorpusWide::test_every_tracked_strata_file_symbol_count_matches_grammar_declared_count
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 89a73237d8ff467b5bd4fe8e0f1507a6a2d92375
---
Direct residue of T-2194 (see T-2328 for the land defect that caused
this): T-2194's own capability grant to design/frob.strata (may "exec"
and may "fs.read" via "tests/unit/test_lang_strata.py", needed by its
new TestGrammarAuthoritativeSymbolsCorpusWide corpus-wide regression
test, which calls subprocess.run and Path.read_text()) was silently
dropped by land and never reached main.

Confirmed on main (commit 230828040a32f2cfa430472caf98f6102ba63134):
`frob check --only gates-security` logs:
  WARNING: strata effects: undeclared capability effect
  tests/unit/test_lang_strata.py:423 exec (subprocess.) on testsuite
  WARNING: strata effects: undeclared capability effect
  tests/unit/test_lang_strata.py:439 fs.read (read_text() on testsuite

WANTED: add tests/unit/test_lang_strata.py to design/frob.strata's
testsuite node's may "exec" and may "fs.read" via-lists (same two-line
edit T-2194 already made and verified once; simply re-landing it).