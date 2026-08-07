---
id: T-1134
title: 'gates: INV006 split-assist -- detect verbatim-moved claim prose and carry/suggest
  the source file''s waiver'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/dup/**
- tests/test_gates.py
- docs/modules/gates.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: T-1134 documents the split-assist feature in docs/modules/gates.md
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: sys sync-interface writes public-surface interface= attrs into design/frob.strata
    for the new find_carried_waiver/find_exclusivity_claim_sentences exports
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim
- tests/test_gates.py::TestInv006SplitAssist::test_no_match_when_no_other_file_shares_the_claim
- tests/test_gates.py::TestInv006SplitAssist::test_reworded_claim_is_not_detected_v1_disclosed
- tests/test_gates.py::TestInv006SplitAssist::test_find_exclusivity_claim_sentences_returns_actual_prose
designated_repro_test: null
acceptance:
- text: GIVEN a module split moves docstring/comment prose containing exclusivity
    vocabulary from a file with an INV006 waiver or invariant binding WHEN frob check
    runs on the result THEN the INV006 finding names the source file's existing waiver/binding
    and offers the carried-waiver text as a fix-it (or auto-carries under a flag)
  evidence:
  - tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim
threat: null
component: null
---
Every split this drive (T-1103, T-1107, T-1072, T-1077, T-1081, T-1082) required hand-carrying INV006 calibration-batch waivers to the new modules -- 3 more by the coordinator today (0abc4e3a) after the gates splits redded main. The clone/dup machinery can already detect verbatim-moved prose; INV006 should use it to stop making 'remember the carried waiver' a human step. Also applies to PII012's (file,token)-keyed allowlist entries which have the same code-moves-need-new-entries failure mode (T-1076 precedent).