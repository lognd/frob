---
id: T-0309
title: 'DSL: a trailing ''# noqa''/#-led tail on a directive line silently drops the
  directive'
state: done
kind: bug
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/dsl.py
- tests/unit/graph/test_dsl.py
- docs/modules/graph.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense narrative into cited ticket body per T-4691 C5 sweep
  actor: logan
  at: '2026-09-19'
  old_length: 619
  new_length: 1931
evidence:
- tests/unit/graph/test_dsl.py::TestNoqaTail::test_waive_with_trailing_noqa_parses
- tests/unit/graph/test_dsl.py::TestNoqaTail::test_tests_with_trailing_bare_noqa_binds
- tests/unit/graph/test_dsl.py::TestNoqaTail::test_hash_inside_quoted_value_is_preserved
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FROBLEMS (lithos W2b): appending '  # noqa: E501' to a frob:tests/frob:waive directive (to satisfy ruff 88-col on a long symref) makes _parse_attrs leftover non-empty -> MalformedDirective, edge dropped, only a debug log. ~50 directives silently regressed to unbound. A directive sharing a physical line with a linter-suppression comment is a reasonable pattern once a repo enforces both. Fix: _parse_attrs should strip a trailing '#'-led tail (noqa or any comment) from leftover before the emptiness check. Same subsystem as T-0286/T-0294. Test: 'frob:waive RULE reason="x"  # noqa: E501' parses to a valid waive edge.

<!-- narrative-moved:src/frob/graph/dsl.py:863:T-0309 -->
T-0309: a directive can legitimately share a physical line with a
linter-suppression comment (a ruff `noqa` marker, say) once a repo
enforces both frob and a linter's line-length rule. Strip a trailing
'#'-led tail from `leftover` before judging it non-empty. This is safe
against a '#' inside a quoted attribute value (e.g. reason="uses
#hashtag"): `_ATTR_RE.sub` above has already consumed any such quoted
value in full (the regex's `"[^"]*"` group matches through the closing
quote), so a '#' that survives into `leftover` was never inside quotes.

T-3856: the tail split must require the '#' to be PRECEDED BY
WHITESPACE. The prior `leftover.split("#", 1)[0]` split on the FIRST
'#' anywhere, so a leftover that itself BEGAN with '#' (genuinely
malformed attribute syntax, not a linter tail) split to an empty
string and the whole directive was silently accepted as attribute-
free -- a hash-tail guard meant for a trailing linter-suppression
marker was swallowing "#garbage" too. `(?<=\s)#` only matches a '#' with
whitespace immediately before it, so a leading hash (no preceding
whitespace within the leftover) never matches and falls through to
the malformed-attribute-syntax check below, unchanged from before
this ticket for every other case.