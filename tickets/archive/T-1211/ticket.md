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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_secrets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4770: preserve exact measurement numbers trimmed from _secrets.py'
  actor: logan
  at: '2026-09-19'
  old_length: 469
  new_length: 1552
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
anchor: false
anchor_reason: null
land_commit: null
---
Root cause: gates/_secrets.py:932 _scan_line loops 33 compiled patterns via finditer per line; _fake_marker_reason (:676) also runs a regex against every line and its predecessor regardless of hits. Fix: one combined alternation regex over the whole file text, offset->line via bisect, defer per-pattern/_fake_marker_reason logic to actual hits. Companion lint rule on the sibling PERF01x-detectors ticket: 're.finditer with a pattern-list loop inside a per-line loop'.


T-4770 follow-up (condensed from a comment above ALL_PROVIDERS/
_candidate_line_indices in src/frob/gates/_secrets.py, trimmed for
DOCARCH002's 12-line cap): this was perf report candidate #6. Exact
measured scale: 544k lines x 33 patterns = ~18M finditer calls -- the
cost is Python-level per-call/regex-engine-setup overhead multiplied
544k-fold, not the character-scanning itself. The combined-alternation
regex comparison (~19s vs ~4.4s baseline) was confirmed empirically on
this repo's own tree, not assumed: a single compiled pattern's
literal-prefix fast path is defeated the moment 33 unrelated literal
prefixes are OR'd into one pattern, so scanning with one combined regex
tries all 33 branches at every character position instead of skipping
ahead via one literal's own prefix scan. Every char class that could
otherwise cross a line (`.`, `\s`) is either bounded by `.`'s default
no-newline-match semantics or a NEGATED class excluding `\s` (hence
`\n`), so mapping a match start offset to its containing line via
_line_offsets/bisect is exact, not an approximation.