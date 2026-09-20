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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense language-tag-synonym rationale into T-1181 body
  actor: logan
  at: '2026-09-19'
  old_length: 319
  new_length: 1323
evidence:
- tests/unit/arch_suite/test_abstraction.py::TestLanguageParityExclusion::test_long_form_language_spellings_normalize_to_short_tag
- tests/unit/arch_suite/test_abstraction.py::TestLanguageParityExclusion::test_long_and_short_form_parity_group_not_flagged
designated_repro_test: null
acceptance:
- text: GIVEN same-signature groups whose member names differ only by language tag
    WHEN the language-parity family exclusion runs THEN the synonym map recognizes
    python/typescript/kotlin/cplusplus alongside the short forms, measured before/after
    on the T-1083 finding set
  evidence:
  - tests/unit/arch_suite/test_abstraction.py::TestLanguageParityExclusion::test_long_form_language_spellings_normalize_to_short_tag
  - tests/unit/arch_suite/test_abstraction.py::TestLanguageParityExclusion::test_long_and_short_form_parity_group_not_flagged
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Refile from the w20-arch T-1083 disposition pass (draft died with the fail-log; full record on branch w20-arch commit a8085d7f): _is_language_parity_family's synonym map lacks the long-form language spellings, so genuinely-parity families with those tags escape the exclusion and pollute abstraction-opportunity counts.

<!-- narrative-moved:src/frob/arch/_abstraction.py:234:T-1181 -->
: T-1181 (refiled from the T-1083 disposition, w20-arch a8085d7f): a
: same-signature parity family sometimes spells its per-language segment
: out in FULL (`python`/`typescript`/`kotlin`/`cplusplus`) rather than
: `_LANGUAGE_TAGS`' short form (`collect_python_tests`/
: `collect_typescript_tests`/... in `frob.testing._collect*`) -- the short
: form alone never matches `python` as a whole underscore-delimited
: segment (it is not a substring of any short tag), so these genuinely-
: parity families fell through uncaught and polluted the abstraction-
: opportunity count as false positives. This maps each long form to its
: canonical short tag so `_language_tag` normalizes both spellings to the
: SAME identity before the distinctness check in
: `_is_language_parity_family` runs -- `rust`/`cpp` have no separate long
: form in this codebase's own naming convention, so they are omitted
: rather than guessed at.
frob:ticket T-1195