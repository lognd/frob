---
id: T-3545
title: 'real-CHANGELOG malformed markdown directive: a recent fragment carries a code-span
  directive that parses as malformed'
state: in-progress
kind: bug
origin: human
created: '2026-08-31'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/graph/test_dsl_markdown_waive.py
- changelog.d/T-3520.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: changelog.d/**
  reason: 'measured: CHANGELOG.md:752 traces to changelog.d/T-3520.md''s own fragment
    text, which mentions ''<!-- frob:waive INV003/INV004 reason=...'' as bare prose
    (not backtick-fenced), so the markdown DSL parser reads it as a live directive
    attempt instead of a mention -- narrowing from the 738-file changelog.d/** glob
    to the single actual source file.'
  actor: logan
  at: '2026-08-31'
- op: add
  glob: changelog.d/T-3520.md
  reason: 'measured: CHANGELOG.md:752 traces to changelog.d/T-3520.md''s own fragment
    text, which mentions ''<!-- frob:waive INV003/INV004 reason=...'' as bare prose
    (not backtick-fenced), so the markdown DSL parser reads it as a live directive
    attempt instead of a mention -- narrowing from the 738-file changelog.d/** glob
    to the single actual source file.'
  actor: logan
  at: '2026-08-31'
evidence:
- tests/unit/graph/test_dsl_markdown_waive.py::TestChangelogMultiLineCodeSpanMention::test_changelog_d_fragments_have_no_unfenced_waive_mention
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED run 33353658750: tests/unit/graph/test_dsl_markdown_waive.py::TestChangelogMultiLineCodeSpanMention::test_real_changelog_has_no_malformed_markdown_directive fails: assert [MalformedDir...ses nothing')] == []. A recently landed changelog.d/ fragment or CHANGELOG.md entry contains a frob directive inside a code span that the markdown DSL parser reads as malformed. Find it (run the test locally, it names the file/line), fix the FRAGMENT via the sanctioned path (regenerate or reword; changelog.d is land-owned) or, if the generator produced it, fix the generator note sanitization; state which.