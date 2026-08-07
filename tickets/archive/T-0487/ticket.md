---
id: T-0487
title: 'dup: python-centric _KEYWORDS misclassifies rust/ts/c/cpp keywords (let/fn/etc)
  as identifiers in R5 def-use labeling'
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/_pipeline.py
- src/frob/dup/_exhaustiveness.py
- tests/test_dup.py
- tests/test_dup_exhaustiveness.py
- pyproject.toml
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/dup/_exhaustiveness.py
  reason: coordinator mission explicitly directs updating DUP_MATRIX_EXCUSES/DUP_CLAIMS
    in the same ticket, per T-0447's already-landed R3 work
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_dup.py
  reason: regression test for the per-grammar keyword fix belongs alongside TestCrossLanguageR5Litmus
    (tests/test_dup.py), which already documents this exact gap; DUP_CLAIMS/DUP_MATRIX_EXCUSES
    update needs its drift-lock test file updated in the same ticket
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_dup_exhaustiveness.py
  reason: regression test for the per-grammar keyword fix belongs alongside TestCrossLanguageR5Litmus
    (tests/test_dup.py), which already documents this exact gap; DUP_CLAIMS/DUP_MATRIX_EXCUSES
    update needs its drift-lock test file updated in the same ticket
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 gate requires a version bump + frob release stamp for this ticket's
    public API change (new DUP_CLAIMS entries); stamping touches these three files
    as a side effect
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 gate requires a version bump + frob release stamp for this ticket's
    public API change (new DUP_CLAIMS entries); stamping touches these three files
    as a side effect
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 gate requires a version bump + frob release stamp for this ticket's
    public API change (new DUP_CLAIMS entries); stamping touches these three files
    as a side effect
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_dup.py::TestCrossLanguageR5WithLet::test_r5_fires_across_languages_with_a_let_binding
- tests/test_dup.py::TestR3LiteralAbstraction::test_r3_fires_where_r2_does_not
- tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_no_unclaimed_cells
- tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_no_cell_is_both_claimed_and_excused
designated_repro_test: null
threat: null
component: null
---
Found while working T-0447 (tests/test_dup.py::TestCrossLanguageR5Litmus). _KEYWORDS is a python-only keyword set; a Rust let in a let_declaration is not recognized as a keyword, so _assignment_ids mis-labels it as an extra 'def' node, diverging the def-use graph from an equivalent Python function's graph. Needs a per-grammar keyword set (mirroring _BLOCK_LABELS/_ASSIGNMENT_LABELS's per-language pattern) so R5 cross-language structural matching is not accidentally broken by declaration-keyword tokens. Also: T-0447 only implements two of R3's three named canonicalizations (literal abstraction + elif control-flow desugar); commutative-operand reordering and real for/while loop-shape desugaring still need AST structure, not a token fold -- tracked as future work here too. Also: frob.dup._exhaustiveness.DUP_MATRIX_EXCUSES' r3-vs-r2 excuse (and the non-python r3/r5 language-gap excuses) should be updated to DUP_CLAIMS now that tests/test_dup.py proves r3 fires independently of r2 and r5 fires cross-language python/rust -- out of T-0447's declared scope (src/frob/dup/_exhaustiveness.py not in scope).