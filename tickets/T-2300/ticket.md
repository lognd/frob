---
id: T-2300
title: unlanded-branch directive signal should reuse the real comment-DSL parser instead
  of a bare regex
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_unlanded.py
- tests/unit/test_unlanded_branch_work.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_unlanded_branch_work.py
  reason: T-2300 repro/positive-control tests for the real comment-DSL parser switch
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_real_directive_anchor_still_flagged_via_real_parser
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_real_ticket_id_inside_a_string_literal_is_not_flagged
designated_repro_test: tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_real_ticket_id_inside_a_string_literal_is_not_flagged
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 0a15f3cce4c959ddf42c220e31cb056f893652f4
---
found while working T-2287.

T-2287 narrowed `_directive_anchor_signals_on_branch`'s (src/frob/tickets/_unlanded.py)
`frob:ticket T-####` detection to require the matched id to RESOLVE to a
real ticket (present in branch_states or main_states) before reporting a
finding. This is option (b) from T-2287's own body: a narrowing
heuristic, not a real parse. It closes the measured 239/244 false-positive
incident (fixture ids with no ticket.md anywhere), but it does NOT close
the residual gap the ticket named explicitly: a commented-out (or
docstring-quoted) mention of a REAL, still-open ticket id still matches
and produces a finding, since the bare regex `_TICKET_DIRECTIVE_RE`
cannot distinguish a live directive comment from prose/commentary that
happens to reference a real id (a specific instance was observed live
during T-2287's own work: this file's own pre-existing test fixture,
test_directive_anchored_code_with_queued_ticket_is_flagged, embeds the
literal string "frob:ticket T-1691" as fixture text, and T-1691 is a real
non-terminal ticket -- so T-2287's own branch showed a transient
"T-1691@t-2287" finding for the ticket's own worktree lifetime).

FIX DIRECTION: reuse this repo's real comment-DSL parser (the one
`frob.graph` uses to resolve `frob:ticket`/`frob:tests`/... directives
during a normal gate run) for the directive-anchor signal, instead of
`_TICKET_DIRECTIVE_RE`'s bare blob-text regex. A real parse can tell a
directive comment apart from a string literal or prose mention by
position/syntax, which a lexical match structurally cannot -- the same
"token/grammar fixes, never lexical" lesson T-2287 itself was filed
under.

POSITIVE CONTROL REQUIRED: a specimen that plants a real id inside a
STRING LITERAL or prose comment (not a directive-position comment) and
asserts the real-parser signal does NOT fire for it, alongside the
existing genuine-directive-anchor specimen which must still fire.