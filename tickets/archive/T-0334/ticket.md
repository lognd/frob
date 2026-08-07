---
id: T-0334
title: 'frob.lang: give cross-grammar node vocabulary so dup R1-R3 bucket structurally,
  not lexically'
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/lang/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_lang_primitives.py::TestCanonicalTokensCrossGrammarVocabulary::test_shares_structural_tags_across_python_and_typescript
- tests/unit/test_lang_primitives.py::TestCanonicalTokensCrossGrammarVocabulary::test_identifier_and_literal_renaming_does_not_change_body_norm
- tests/unit/test_lang_primitives.py::TestCanonicalTokensCrossGrammarVocabulary::test_unmapped_keyword_falls_back_to_other_tag
- tests/unit/test_lang_primitives.py::TestCanonicalTokensCrossGrammarVocabulary::test_deterministic_and_reformatting_insensitive
designated_repro_test: null
threat: null
component: null
---
T-0198's cross-language clone litmus (tests/test_dup_cross_lang.py) proved empirically that find_clones reports ZERO groups for the same accumulator-with-clamp logic written in Python vs TypeScript, at every threshold from 0.9 down to 0.1. Root cause: src/frob/dup/_pipeline.py's R1 (_r1_hash) and R2 (_r2_hash/_r2_normalize) bucket on literal body_tokens -- R2 alpha-renames identifier-shaped tokens but passes every keyword/punctuation token through unchanged, and R3 (_r3_fingerprint) is computed over the R2-normalized stream. Python's def/for/in/: and TypeScript's function/for/of/{ }/; share no token vocabulary, so R1/R2 buckets never collide across the pair and candidate_pairs (frob_core) never surfaces the pair to R4/R5 verification -- lowering the threshold cannot help since the miss happens before any similarity comparison. docs/modules/dup-sota-survey.md item 13 flagged this exact risk and recommended the litmus fixture as verification; the verification came back negative. Fix direction (not designed here): frob.lang would need a shared cross-grammar node-KIND vocabulary (e.g. a canonical 'for_loop'/'if_stmt'/'call' tag per RawSymbol token or node) so R1-R3 could bucket structurally instead of lexically. Out of T-0198's scope (src/frob/dup/**, tests/**, tickets.md only; src/frob/lang/** untouched).