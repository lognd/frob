---
id: T-1994
title: CHANGELOG.md:1853 DSL001 residual from T-1989 is land-owned, unreachable from
  any worktree
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- CHANGELOG.md
- tests/unit/graph/test_dsl_markdown_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/graph/test_dsl_markdown_waive.py
  reason: regression test reading the real repo CHANGELOG.md lives here, alongside
    the other T-1989 markdown-mention tests it extends
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/graph/test_dsl_markdown_waive.py::TestChangelogMultiLineCodeSpanMention::test_real_changelog_has_no_malformed_markdown_directive
designated_repro_test: tests/unit/graph/test_dsl_markdown_waive.py::TestChangelogMultiLineCodeSpanMention::test_real_changelog_has_no_malformed_markdown_directive
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1989's mention/use fix for markdown DSL001 (code-span-aware masking,
_blank_code_spans) resolves 104 of the 105 findings T-1968's land
produced. The one holdout is structurally unreachable from any worktree:

  CHANGELOG.md:1853  DSL001 (verb='waive'): a historical CHANGELOG entry
  quotes `<!-- frob:waive INV003|INV004 reason="..." -->` as a worked
  example, wrapped in a MULTI-LINE inline-code span (the backtick opens
  on one line, closes on the next after prose wrapping).

WHY IT IS NOT FIXED: `_blank_code_spans` deliberately only masks
SAME-LINE inline-code spans (see its own docstring) -- a whole-file
regex allowing multi-line spans was tried and measured UNSAFE:
docs/modules/gates.md alone carries an odd total backtick count (7657 at
measurement time), so non-greedy file-wide pairing silently mispairs
everything downstream of a single stray backtick. The two OTHER
multi-line-span mentions this same investigation found
(docs/modules/graph.md, docs/modules/gates.md) were fixed by rewrapping
the doc prose onto one line instead -- the same fix is not available
here because CHANGELOG.md is land-owned (docs/guides/agent-playbook.md
section 4b, T-0731): a worktree's `pre-commit` hook hard-refuses ANY
commit whose staged CHANGELOG.md diverges from main's own content,
`FROB_LAND_INTERNAL` unset (verified by reading the hook directly,
`.git/hooks/pre-commit`'s `_t1742_staged_diverges_from_main` check).

FIX DIRECTION: a one-line edit rewrapping CHANGELOG.md:1853-1854's
example onto a single physical line, made either (a) by a coordinator
shell with `FROB_LAND_INTERNAL=1` set deliberately for this one edit, or
(b) folded into a future `frob ticket land` pass. Do not weaken the
land-owned-file guard to work around this -- it is protecting exactly
the right thing (T-0731's original bump-and-chase incident).