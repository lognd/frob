---
id: T-2177
title: 'frob ticket new accepts a scope whose files contain no trace of the ticket''s
  own subject: two tickets were filed against a file with zero matching code, caught
  only by the implementing agent'
state: queued
kind: feature
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_new.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'Scope-plausibility matching MUST be token/grammar based, never lexical. Parse
    the ticket text and each scope file with the language grammar and compare SYMBOL
    sets (identifiers, qualified names, tokenized error-string literals). Never substring
    or regex match: a grep-style ''file contains this text'' check passes on a comment
    merely mentioning the symbol and fails on a re-exported alias -- wrong in both
    directions. This test MUST fail against current main.'
  evidence: []
- text: Given a ticket whose title names a symbol defined in file A, when the declared
    scope lists only unrelated file B, then ticket new refuses or warns loudly --
    reproducing the two real misfilings (T-2157 and T-2173, both scoped to src/frob/tickets/_land_git_ops.py,
    which contains zero matching code; git grep -c rebase on that file returns 0).
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
