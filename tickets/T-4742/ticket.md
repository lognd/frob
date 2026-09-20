---
id: T-4742
title: 'Separator canonicalization to path::Class.method: lint plus Tier-A fix, parser
  never refuses a spelling'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4713
parent: T-4703
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_separator_canon.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
- tests/test_gates_separator_canon.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Leaf 6 of T-4703. 2 points. Separator canonicalization. Blocked by leaf 4 only for the shared
`_KNOWN_GATE_RULES` / docs/modules/gates.md edit; the logic is independent.

## What to build

The parser accepts three spellings of the same symref: `path::Class.method`,
`path::Class::method`, and `path.Class.method`. Canonical is `path::Class.method` -- what pytest
prints, so a node id copied out of a pytest run is already canonical.

(a) A lint flagging the two non-canonical spellings.
(b) A Tier-A fix rewriting them, in the `_fix_engine_text.py` line-scoped handler family, with
    the same `only_paths` scoping discipline as `fix_fmt001_directive_wrap`
    (src/frob/gates/_fix_engine_text.py:113-150, T-1391: a whole-tree rewrite is an
    out-of-scope WRITE that land rejects).
(c) The parser NEVER refuses a non-canonical spelling. Owner directive: token/grammar fixes,
    never lexical. The lint reports, the fix rewrites, the parse always succeeds.
(d) Rule registration in src/frob/gates/_waive.py's `_KNOWN_GATE_RULES` plus the
    docs/modules/gates.md rule table.

Relevant prior finding: src/frob/graph/dsl.py:1401-1420 records T-0265, where a mismatched
separator convention (a directive using pytest's `Class::method` while the graph's own qualname
is `Class.method`) produced a genuinely dangling edge that slipped past a ticket-scoped check.
That is the incident this leaf makes impossible; cite it in the rule's docs.

## Positive control

- Plant one directive in each of the three spellings, all naming the SAME symbol, and assert
  they resolve to the same edge (the parser's tolerance) AND that exactly two of them are
  flagged (the lint's discrimination).
- Plant a path that legitimately contains a dot but no class (`a.b.py::f`) and assert it is NOT
  rewritten -- the fix must not treat every dot as a separator.
- Plant a quoted value containing `::` and assert it is untouched.

## Acceptance

- All three spellings parse to identical edges; two are flagged; the fix converges in one pass
  and is idempotent on the second.
- Repo-wide count of each non-canonical spelling before and after, in the Done report.