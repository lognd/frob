---
id: T-1181
title: 'arch: language-parity exclusion synonym map missing python/typescript/kotlin/cplusplus
  spellings'
state: done
kind: bug
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestLanguageParityExclusion::test_long_form_language_spellings_normalize_to_short_tag
- tests/unit/test_arch.py::TestLanguageParityExclusion::test_long_and_short_form_parity_group_not_flagged
designated_repro_test: null
acceptance:
- text: GIVEN same-signature groups whose member names differ only by language tag
    WHEN the language-parity family exclusion runs THEN the synonym map recognizes
    python/typescript/kotlin/cplusplus alongside the short forms, measured before/after
    on the T-1083 finding set
  evidence:
  - tests/unit/test_arch.py::TestLanguageParityExclusion::test_long_form_language_spellings_normalize_to_short_tag
  - tests/unit/test_arch.py::TestLanguageParityExclusion::test_long_and_short_form_parity_group_not_flagged
threat: null
component: null
---
Refile from the w20-arch T-1083 disposition pass (draft died with the fail-log; full record on branch w20-arch commit a8085d7f): _is_language_parity_family's synonym map lacks the long-form language spellings, so genuinely-parity families with those tags escape the exclusion and pollute abstraction-opportunity counts.