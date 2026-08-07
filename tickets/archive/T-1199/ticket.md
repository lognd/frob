---
id: T-1199
title: 'refactor: directive/waiver carrier (absorbs T-1134)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
blocked_by:
- T-1197
parent: T-1197
tier: ticket
sprint: null
scope:
- src/frob/refactor/**
- tests/test_refactor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/graph/dsl.py
  reason: reads/calls into these modules but does not modify them; scope narrowed
    to the new refactor carrier module
  actor: logan
  at: '2026-07-29'
- op: remove
  glob: src/frob/gates/_waive.py
  reason: reads/calls into these modules but does not modify them; scope narrowed
    to the new refactor carrier module
  actor: logan
  at: '2026-07-29'
- op: remove
  glob: src/frob/graph/lock.py
  reason: reads/calls into these modules but does not modify them; scope narrowed
    to the new refactor carrier module
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_refactor.py::TestDirectiveCarrier::test_attached_waiver_moves_with_symbol
- tests/test_refactor.py::TestDirectiveCarrier::test_move_carries_attached_waiver_end_to_end
- tests/test_refactor.py::TestDirectiveCarrier::test_directive_target_elsewhere_rewritten
- tests/test_refactor.py::TestDirectiveCarrier::test_lock_ack_carried_to_new_symref
designated_repro_test: null
acceptance:
- text: 'GIVEN a symbol with a `frob:waive ARCH101 reason="..."` placed directly

    above it WHEN it is moved to a new file via `frob refactor move` THEN the

    waiver moves with it and `frob.gates._waive._match_waiver`''s per-symbol

    exact-symref mode still matches the moved symbol''s new `path::qualname`,

    with no new unwaived ARCH101 finding at the new location'
  evidence:
  - tests/test_refactor.py::TestDirectiveCarrier::test_attached_waiver_moves_with_symbol
  - tests/test_refactor.py::TestDirectiveCarrier::test_move_carries_attached_waiver_end_to_end
- text: 'GIVEN a `frob:doc docs/x.md#anchor` directive attached to a different,

    non-moving symbol elsewhere in the repo, whose target names a symbol that

    IS moving WHEN the move completes THEN that directive''s target string is

    rewritten to the new path::qualname too'
  evidence:
  - tests/test_refactor.py::TestDirectiveCarrier::test_directive_target_elsewhere_rewritten
- text: 'GIVEN a moved symbol with an existing frob.lock ack at its old symref and

    an unchanged digest WHEN the move completes THEN the ack is carried

    forward to the new symref rather than reported stale by DRIFT001'
  evidence:
  - tests/test_refactor.py::TestDirectiveCarrier::test_lock_ack_carried_to_new_symref
threat: null
component: null
---
Design: docs/design/refactor-verb.md (T-1135). Absorbs T-1134 (done):
reuse its `find_carried_waiver` helper, already written reusable/
standalone per T-1134's own Done report, as the seed for this carrier.

Extends T-1197's plan/apply pipeline with the frob-owned DSL reference
kinds: for a moving symbol, rewrite every `frob:*` comment-DSL directive
whose TARGET names it (frob:doc, frob:tests, frob:enforces,
frob:uses-contract, frob:invariant, frob:ticket, frob:todo, frob:decision,
frob:channel, frob:boundary, frob:secret, frob:protocol, frob:transition,
frob:requires, frob:acquire, frob:release, frob:escapes -- the full
frob.graph.dsl._VERB_TABLE), using frob.graph.dsl's existing parser, not a
second regex.

Also rewrites `frob:waive RULE reason="..."` `src` symrefs, preserving
frob.gates._waive._match_waiver's three matching modes (per-symbol exact
symref, file-scoped, package/system-prefix) -- a waiver's src is itself a
symref that must move with the same rules as a frob:doc target. This is
the direct fix for the ARCH101/103 waiver-symref path:: bug named in
T-1135's epic body.

Carries frob.lock ack entries forward: an ack keyed on (symbol identity,
digest) at the old symref, where the digest is unchanged by the move,
gets re-keyed to the new symref rather than going stale.

Scope note: this ticket rewrites directive/waiver TARGETS repo-wide (per
epic acceptance [2] -- a directive anywhere in the repo pointing at the
moved symbol, not just directives attached to the moved symbol's own
code) but does not move the owning code itself; T-1197 (or the split
verb, T-1201) does that.