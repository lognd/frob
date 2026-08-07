---
id: T-1211
title: 'perf: secrets gate 33 regexes x finditer per line -- one combined-alternation
  scan per file'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/gates/_secrets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_secrets_gate.py::TestOverlapClaim::test_embedded_overlapping_match_is_not_double_claimed
- tests/test_secrets_gate.py::TestFindsTokens::test_anthropic_key_flagged_sec001
- tests/test_secrets_gate.py::TestFakeMarking::test_fake_marker_same_line
- tests/test_secrets_gate.py::TestDriftLock::test_every_provider_has_a_fixture
designated_repro_test: null
acceptance:
- text: 'GIVEN _scan_line runs 33 compiled patterns x finditer per line (544k lines,
    17.97M finditer calls, 94 pct of the gate) plus _fake_marker_reason regex against
    every line WHEN the whole file text is scanned once with one combined alternation
    regex (named groups per provider), match offsets map to lines via a bisect line-offset
    index, and per-pattern logic plus _fake_marker_reason only run on the rare hits
    THEN secrets drops from 4.5s to well under 1s native (report candidate #6)'
  evidence:
  - tests/test_secrets_gate.py::TestOverlapClaim::test_embedded_overlapping_match_is_not_double_claimed
  - tests/test_secrets_gate.py::TestFindsTokens::test_anthropic_key_flagged_sec001
  - tests/test_secrets_gate.py::TestFakeMarking::test_fake_marker_same_line
  - tests/test_secrets_gate.py::TestDriftLock::test_every_provider_has_a_fixture
threat: null
component: null
---
Root cause: gates/_secrets.py:932 _scan_line loops 33 compiled patterns via finditer per line; _fake_marker_reason (:676) also runs a regex against every line and its predecessor regardless of hits. Fix: one combined alternation regex over the whole file text, offset->line via bisect, defer per-pattern/_fake_marker_reason logic to actual hits. Companion lint rule on the sibling PERF01x-detectors ticket: 're.finditer with a pattern-list loop inside a per-line loop'.