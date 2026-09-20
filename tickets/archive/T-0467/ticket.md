---
id: T-0467
title: 'refs tokenizer backtick blind spot: _refs.py _QUOTED_RE matches only quotes
  and []() links, never backtick-wrapped paths (repo doc convention) -- 12 legit-linked
  .md docs read as REF001 orphans (false positives, distinct from T-0466)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_refs.py
- tests/test_refs_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4770: preserve backtick-regex test-proof detail trimmed from _refs.py'
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 447
evidence:
- tests/test_refs_gate.py::TestBacktickTokenizer::test_backtick_wrapped_path_mention_counts_as_reference
- tests/test_refs_gate.py::TestBacktickTokenizer::test_backtick_wrapped_bare_identifier_not_treated_as_reference
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

T-4770 follow-up (condensed from _BACKTICK_RE's docstring in
src/frob/gates/_refs.py, trimmed for DOCARCH002's 12-line cap): the
example is `docs/rework.md` (real path) vs `manifest.yaml` in a
sentence that merely DESCRIBES the file ("the manifest.yaml file lists
things, but nothing loads it") without being a real reference --
exactly the false PASS TestReferenceDetection.
test_bare_prose_mention_does_not_count_as_a_reference guards against.