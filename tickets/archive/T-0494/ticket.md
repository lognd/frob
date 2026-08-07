---
id: T-0494
title: 'tests/test_dup_cross_lang.py: T-0198 characterization test now wrong -- R5
  correctly fires cross-language python/typescript after T-0487''s keyword fix'
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_dup_cross_lang.py
- docs/modules/dup.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/dup.md
  reason: mission instructions require updating dup.md's now-stale 'only python is
    proven cross-rung' claim to reflect T-0494's r5/python-typescript positive finding
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_dup_cross_lang.py::TestCrossLanguageR5NowFires::test_r5_group_fires_at_every_threshold[0.9]
- tests/test_dup_cross_lang.py::TestCrossLanguageR5NowFires::test_r5_group_fires_at_every_threshold[0.1]
- tests/test_dup_cross_lang.py::TestCrossLanguageR5NowFires::test_r5_group_is_not_gated_by_a_threshold_above_its_own_similarity
- tests/test_dup_cross_lang.py::TestCrossLanguageCloneNotYetDetected::test_both_languages_parse_into_the_snapshot
- tests/test_dup_cross_lang.py::TestCrossLanguageCloneNotYetDetected::test_both_symbols_are_individually_fingerprinted
designated_repro_test: null
threat: null
component: null
---
found while working T-0487: the _KEYWORDS python-centric-keyword fix (frob.dup._pipeline) makes R5 correctly recognize TypeScript's 'let'/'const' as declaration keywords instead of mis-labeling them as identifiers, so _real_dataflow_graph now builds a structurally-correct def-use graph for tests/fixtures/dup_cross_lang's mod_b.ts::computeTotal -- and it now genuinely WL-hash-collides with mod_a.py::compute_total at r5, similarity=0.88, verified directly against find_clones. This is a real accuracy improvement (R5 is documented as structural/language-agnostic, T-0196/T-0199), not a regression, but it makes tests/test_dup_cross_lang.py::TestCrossLanguageCloneNotYetDetected::test_no_clone_group_at_any_threshold (asserting report.groups == () at every threshold) fail: 5 parametrized cases now see a real r5 group. The test's docstring/module-level claim ('cross-grammar structural bucketing... tracked as a follow-up') needs updating to reflect that R5 already closes this specific case; the test needs to assert r5 DOES fire (or drop the blanket 'zero groups' assertion and characterize per-rung instead), and frob.dup._exhaustiveness's r5/typescript language-gap excuse likely needs a DUP_CLAIMS entry the same way T-0487 added one for r5/rust. Out of T-0487's declared scope (tests/test_dup_cross_lang.py not in T-0487's scope).