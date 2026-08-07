---
id: T-1543
title: v2_state_transitions silently drops transitions when git detects a false copy
  across similar ticket files
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets.py::TestV2StateTransitions::test_byte_similar_sibling_ticket_does_not_drop_transitions
designated_repro_test: null
threat: null
component: null
---
Discovered while writing T-1330's v1/v2 parity benchmark:
v2_state_transitions (src/frob/tickets/_store.py, T-1257) calls
`git log --reverse --follow -p -- tickets/T-####/ticket.md`. When a
NEW ticket's initial content is >=50% byte-similar to another
ticket's ticket.md as it exists in that same commit's tree (common,
since every v2 ticket.md shares the same templated frontmatter --
id/title/state differ, ~8 other fields identical), git's `-C`-implied
copy detection under `--follow` attributes the new file's creation
commit as a "copy from" the other ticket's file instead of a plain
addition -- and combined with --reverse, git's --follow only reports
that ONE (creation) commit and silently stops, dropping every
subsequent state-transition commit for that ticket entirely.

Reproduced directly: two tickets sharing the standard template,
differing only in id/title/state/body, produced a copy-detected
creation commit for the second ticket and v2_state_transitions
returned only its "queued" transition -- "in-progress" and "done"
(both real, separately committed) were silently missing. This
explains T-1257's own unclosed acceptance criterion #3 (v1/v2 parity)
and directly undermines T-1330's fast path: a repo where two tickets'
files are byte-similar enough (routine for freshly-filed tickets with
short bodies) can silently under-report DONE transitions for `frob
ticket flow`/`sprint velocity` in v2 mode, with no error surfaced.

Fix should live in v2_state_transitions itself: disable copy/rename
detection for this specific git log call (e.g. --no-follow plus a
manual git log --all -- <path> reconstruction that does not depend on
--follow's copy heuristic, or pass a --find-copies-harder=0 equivalent
that suppresses the false attribution) so the mined transition list
is provably complete regardless of a ticket's content similarity to
its siblings. Add a regression test reproducing the exact two-similar-
tickets shape.