---
id: T-2218
title: 'A ticket body that DISCUSSES a waiver is indistinguishable from one that DECLARES
  it: T-2215''s own prose describing the escape-hatch shape would satisfy the BUG003
  waiver regex and self-waive'
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_mutation_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'Measured instance, and it is self-referential: tickets/T-2215/ticket.md:56
    reads ''escape-hatch shape (a `frob:waive BUG003 reason="..."` body-text ...)''
    -- prose DESCRIBING the mechanism, with the directive inside backticks as an example.
    _BUG002_WAIVER_RE (src/frob/gates/_mutation_evidence.py:238, pattern frob:waive\s+BUG00N\s+reason="([^"]*)")
    matches it and extracts ''...'' as the reason. So the ticket that documents the
    waiver mechanism would waive itself. 13 ticket files currently contain a matching
    string; most are genuine declarations, which is exactly why the two cannot be
    told apart today. This test MUST fail against current main.'
  evidence: []
- text: 'Distinguish DECLARATION from DISCUSSION structurally, not by pattern tightening.
    A ticket body is markdown, so the grammar available is markdown''s: a directive
    inside a fenced code block, an inline code span, or a blockquote is being QUOTED,
    not declared. Parse the body as markdown and ignore code spans/blocks -- do not
    reach for frob.lang raw_tree/COMMENT_TYPES here, which answers a different question
    (is line N of a SOURCE file inside a grammar comment) and returns an empty set
    for any path without a registered grammar, including tickets.md. An implementer
    already checked that and was right to refuse it.'
  evidence: []
- text: Do NOT fix this by requiring the directive at column 0 or on its own line
    -- a documenting author will naturally write it on its own line too, and a declaring
    author may indent it under a heading. Do NOT narrow the reason= capture to exclude
    '...' specifically; that fixes one literal and leaves every other quoted example.
    Fix BUG002, BUG003, no-behavior-change and must-still-pass together -- they share
    the same raw regex-over-ticket.body mechanism (_BUG002_WAIVER_RE's precedent is
    cited in-file at line 244), so fixing one leaves the identical hole in the others.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
