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
scope:
- src/frob/gates/_refs.py
- tests/test_refs_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_refs_gate.py::TestBacktickTokenizer::test_backtick_wrapped_path_mention_counts_as_reference
- tests/test_refs_gate.py::TestBacktickTokenizer::test_backtick_wrapped_bare_identifier_not_treated_as_reference
designated_repro_test: null
threat: null
component: null
---
