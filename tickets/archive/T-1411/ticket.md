---
id: T-1411
title: 'PII012 comment sweep is a grep, not structural: prose about a "token" errors
  the gate'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
blocked_by:
- T-1235
parent: T-1402
tier: ticket
sprint: null
scope:
- src/frob/gates/_pii_structural/_keywords.py
- tests/test_pii_structural_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_pii_structural_gate.py
  reason: 'Re-registering tests/test_pii_structural_gate.py in T-1411''s scope --

    the coordinator''s earlier scope grant (commit e1f9daec) was dropped by a

    ledger-splice merge (c46abf91 took "ours" for this ticket''s block

    wholesale, since T-1411''s own in-progress/blocked_by state was also

    touched on this branch). T-1235''s tests/** lease is confirmed released

    (state: queued), so this should now be a clean add.

    '
  actor: logan
  at: '2026-08-01'
evidence:
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_standalone_prose_comment_with_no_referenced_identifier_does_not_fire
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_comment_keyword_fires
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_ordinary_comment_mentioning_secret_still_fires
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_standalone_comment_in_reference_form_naming_real_field_fires
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_standalone_comment_matching_in_scope_identifier_fires
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_hash_inside_string_literal_is_not_treated_as_comment
designated_repro_test: null
acceptance:
- text: GIVEN a comment using a FIELD_SIGNATURES word as ordinary prose with no correspondingly-named
    identifier in scope WHEN the PII gate runs THEN PII012 does not fire
  evidence:
  - tests/test_pii_structural_gate.py::TestKeywordSweep::test_standalone_prose_comment_with_no_referenced_identifier_does_not_fire
- text: GIVEN a comment naming a real in-scope identifier that holds person-related
    data WHEN the PII gate runs THEN PII012 still fires exactly as today, proven by
    a regression test
  evidence:
  - tests/test_pii_structural_gate.py::TestKeywordSweep::test_comment_keyword_fires
  - tests/test_pii_structural_gate.py::TestKeywordSweep::test_ordinary_comment_mentioning_secret_still_fires
  - tests/test_pii_structural_gate.py::TestKeywordSweep::test_standalone_comment_in_reference_form_naming_real_field_fires
  - tests/test_pii_structural_gate.py::TestKeywordSweep::test_standalone_comment_matching_in_scope_identifier_fires
- text: GIVEN a hash character inside a string literal WHEN comments are extracted
    THEN it is not treated as starting a comment
  evidence:
  - tests/test_pii_structural_gate.py::TestKeywordSweep::test_hash_inside_string_literal_is_not_treated_as_comment
threat: null
component: null
---
PII012 has two scanners in src/frob/gates/_pii_structural/_keywords.py, and only one of them earns the package's "structural" name.

_scan_identifier_keywords IS structural. It walks the AST and only considers names in positions that can actually hold data: ast.arg, FunctionDef names, ast.Name in Store context, and AnnAssign data-structure field targets. It knows what a name IS before judging it.

_scan_comment_keywords is a grep. It does line.find("#"), takes everything after it, and runs a bare [A-Za-z_]+ word split over the result. No AST, no tokenizer, no consultation of the symbol table the rest of the package relies on. Its own docstring concedes the limitation: a "#" inside a string literal is misread as starting a comment.

Consequence, hit for real on 2026-08-01: a comment written as design rationale -- prose reading "a bare suppression token in source" -- produced two PII012 findings at ERROR severity and blocked the gate. The word "token" was used as ordinary English about text processing. Nothing in the file names, holds, or handles a credential. Rewording human prose to appease a word list is precisely the carpet-bombing this epic exists to stop, and it teaches contributors that the honest fix is to censor their own comments.

Two levels of precision available, both preserving the capability fully:

LEVEL 1, mechanical and cheap. Extract comments with the stdlib tokenize module (COMMENT tokens carry exact extents) rather than a line-oriented "#" search. This alone removes the documented string-literal misread and gives an exact comment span to scan. Strictly better, no behaviour lost.

LEVEL 2, the real precision win. Consult the symbol table the identifier scanner already builds. A comment word should fire only when it plausibly REFERS to something -- it matches an identifier actually in scope in that file, or is written in reference form (backticked, dotted, attached to a nearby declaration) -- rather than appearing as an English word in a sentence. A comment that says "the token is stored unencrypted" next to a real token variable is exactly what this rule should catch, and it still would. A comment that says "wrap mid-token" would not.

The vocabulary is not the problem; the absence of structure around the vocabulary is. FIELD_SIGNATURES is a reasonable keyword set. What is missing is any evidence the matched word is being used as a NAME.

CAPABILITY MUST NOT SHRINK. Do not delete keywords, do not drop the comment scanner, do not lower severity to make findings disappear. Prove the narrowing is honest with regression tests, at minimum:
  - a comment naming a real in-scope identifier that holds person-related data STILL fires
  - a comment using the same word as ordinary prose, with no corresponding identifier, does NOT fire
  - a "#" inside a string literal is not treated as a comment at all

Precedent already in this file: _scan_comment_keywords deliberately skips "# frob:..." directive comments (_FROB_DIRECTIVE_RE, T-0539). So context-sensitive exclusion is an accepted shape here; this ticket generalises it from one hardcoded prefix to actual structure.

Related: _PII012_REVIEWED_NON_PII (T-0540) is a manually-maintained (file, word) allowlist -- a symptom of the same defect. Every entry in it is a case where a human confirmed the word was prose, not a name. If Level 2 lands, most of that table should become unnecessary; check whether it can shrink, and report how much of it survives.